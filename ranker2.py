import pandas as pd
import numpy as np
from math import ceil
import random
import argparse
from faker import Faker
from cparser import CParser


# Try to import tqdm for progress bar, fallback if not available
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


# Text coloring class for use within Window's terminals
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_companies_from_file(file_path: str, num_companies: int) -> list:
    """Load company names from file"""
    out_list = []
    try:
        with open(file_path, 'r') as f:
            for _ in range(num_companies):
                company_name = f.readline().strip()
                if company_name:
                    out_list.append(company_name)
    except FileNotFoundError:
        # Fallback to generated company names if file not found
        fake = Faker()
        out_list = [fake.company() for _ in range(num_companies)]
    
    return out_list


def generate_synthetic_data(num_students: int, num_companies: int) -> pd.DataFrame:
    """Generate synthetic student ranking data with proper unique rankings 1-5"""
    fake = Faker()
    
    # Load company names from file, fallback to generated names
    companies_file = "./utilities/companies.txt"
    company_list = get_companies_from_file(companies_file, num_companies)
    
    # If we couldn't get enough companies from file, generate more
    while len(company_list) < num_companies:
        company_list.append(fake.company())
    
    # Trim to exact number needed
    company_list = company_list[:num_companies]
    
    # Generate student names
    student_names = [fake.name() for _ in range(num_students)]
    
    # Generate proper rankings for each student
    rankings = np.full((num_students, num_companies), 6, dtype=int)  # Start with all unranked (6)
    
    for student_idx in range(num_students):
        # Each student ranks exactly 5 companies (or fewer if there are fewer than 5 companies)
        num_to_rank = min(5, num_companies)
        
        # Randomly select which companies this student will rank
        ranked_company_indices = np.random.choice(num_companies, size=num_to_rank, replace=False)
        
        # Assign RANDOM rankings 1 through num_to_rank to the selected companies
        random_rankings = np.random.permutation(np.arange(1, num_to_rank + 1))
        rankings[student_idx, ranked_company_indices] = random_rankings
    
    # Create DataFrame with proper data types
    df = pd.DataFrame({'Student': student_names})
    
    # Add ranking columns directly as numeric
    for i, company in enumerate(company_list):
        df[company] = rankings[:, i]
    
    return df


def generate_proposed_companies(df: pd.DataFrame) -> dict:
    """Generate random proposed companies mapping for synthetic data - optimized"""
    company_columns = [col for col in df.columns if col != 'Student']
    student_names = df['Student'].tolist()
    
    # Vectorized random selection
    proposed_indices = np.random.randint(0, len(company_columns), len(student_names))
    proposed_companies = {student_names[i]: company_columns[proposed_indices[i]] 
                         for i in range(len(student_names))}
    
    return proposed_companies


def save_trial_input_data(main_df: pd.DataFrame, proposed_companies: dict, ranked_companies_df: pd.DataFrame, trial_num: int, args) -> dict:
    """Collect key input data metrics for a trial - returns summary data instead of saving files"""
    
    # Calculate key input metrics
    company_columns = [col for col in main_df.columns if col != 'Student']
    
    # Company-centric statistical analysis - how students rank each company
    company_ranking_stats = []
    company_names = []
    
    for col in company_columns:
        company_rankings = main_df[col].dropna()
        # Only include actual rankings (1-5), exclude unranked companies (6)
        actual_rankings = company_rankings[company_rankings <= 5]
        
        if len(actual_rankings) > 0:
            company_ranking_stats.append(actual_rankings.values)
            company_names.append(col)
    
    # Calculate statistics across companies (not students)
    company_means = np.array([np.mean(rankings) for rankings in company_ranking_stats])
    company_stds = np.array([np.std(rankings) for rankings in company_ranking_stats])
    
    # Company-level statistical measures
    # 1. Mean of company averages (how popular companies are on average)
    avg_company_ranking = float(np.mean(company_means))
    
    # 2. Standard deviation of company averages (variation in company popularity)
    company_popularity_std = float(np.std(company_means))
    
    # 3. Skewness of company average rankings (are most companies popular or unpopular?)
    if len(company_means) > 2 and company_popularity_std > 0:
        mean_pop = np.mean(company_means)
        company_skewness = float(np.mean(((company_means - mean_pop) / company_popularity_std) ** 3))
    else:
        company_skewness = 0.0
    
    # 4. Kurtosis of company average rankings (tail heaviness in company popularity)
    if len(company_means) > 2 and company_popularity_std > 0:
        company_kurtosis = float(np.mean(((company_means - mean_pop) / company_popularity_std) ** 4) - 3)
    else:
        company_kurtosis = 0.0
    
    # 5. Shannon Entropy of company popularity distribution
    # Bin company averages into discrete categories for entropy calculation
    if len(company_means) > 1:
        # Create bins for company average rankings (1.0-1.5, 1.5-2.0, etc.)
        bins = np.arange(1.0, 6.0, 0.5)
        hist, _ = np.histogram(company_means, bins=bins)
        hist = hist[hist > 0]  # Remove empty bins
        if len(hist) > 0:
            probabilities = hist / np.sum(hist)
            company_entropy = float(-np.sum(probabilities * np.log2(probabilities)))
        else:
            company_entropy = 0.0
    else:
        company_entropy = 0.0
    
    # 6. Company outlier detection (companies with unusual average rankings)
    if len(company_means) > 2:
        q1_comp = np.percentile(company_means, 25)
        q3_comp = np.percentile(company_means, 75)
        iqr_comp = q3_comp - q1_comp
        lower_bound_comp = q1_comp - 1.5 * iqr_comp
        upper_bound_comp = q3_comp + 1.5 * iqr_comp
        
        # Separate outlier detection for highly-ranked (popular) and lowly-ranked (unpopular) companies
        highly_ranked_outliers = company_means[company_means < lower_bound_comp]  # Lower rankings = more popular
        lowly_ranked_outliers = company_means[company_means > upper_bound_comp]   # Higher rankings = less popular
        
        highly_ranked_outlier_count = len(highly_ranked_outliers)
        lowly_ranked_outlier_count = len(lowly_ranked_outliers)
        
        highly_ranked_outlier_percentage = (highly_ranked_outlier_count / len(company_means)) * 100 if len(company_means) > 0 else 0
        lowly_ranked_outlier_percentage = (lowly_ranked_outlier_count / len(company_means)) * 100 if len(company_means) > 0 else 0
        
        # Keep legacy totals for backward compatibility
        company_outlier_count = highly_ranked_outlier_count + lowly_ranked_outlier_count
        company_outlier_percentage = (company_outlier_count / len(company_means)) * 100 if len(company_means) > 0 else 0
    else:
        highly_ranked_outlier_count = 0
        lowly_ranked_outlier_count = 0
        highly_ranked_outlier_percentage = 0.0
        lowly_ranked_outlier_percentage = 0.0
        company_outlier_count = 0
        company_outlier_percentage = 0.0
    
    # Additional company insights
    best_company_avg = float(np.min(company_means)) if len(company_means) > 0 else 0.0
    worst_company_avg = float(np.max(company_means)) if len(company_means) > 0 else 0.0
    company_avg_range = worst_company_avg - best_company_avg
    
    # Company distribution statistics
    company_stats = ranked_companies_df.head(3)  # Top 3 companies
    
    # Company inclusion analysis (how many students included each company in their preferences)
    inclusion_counts = {}
    for company in proposed_companies.values():
        inclusion_counts[company] = inclusion_counts.get(company, 0) + 1
    
    most_included_company = max(inclusion_counts, key=inclusion_counts.get)
    most_included_count = inclusion_counts[most_included_company]
    
    # Return summary metrics with company-centric statistics
    input_summary = {
        'trial': trial_num,
        'total_students': len(main_df),
        'total_companies': len(company_columns),
        'companies_ranked': len(company_names),  # Number of companies that received rankings
        
        # Company-centric statistics
        'avg_company_ranking': avg_company_ranking,  # Average ranking across all companies
        'company_popularity_std': company_popularity_std,  # Variation in company popularity
        'company_ranking_skewness': company_skewness,  # Distribution shape of company averages
        'company_ranking_kurtosis': company_kurtosis,  # Tail heaviness of company popularity
        'company_entropy': company_entropy,  # Diversity in company popularity distribution
        'company_outlier_count': company_outlier_count,  # Number of unusually ranked companies (total)
        'company_outlier_percentage': float(company_outlier_percentage),  # Percentage of outlier companies (total)
        'highly_ranked_outlier_count': highly_ranked_outlier_count,  # Number of extremely popular companies
        'highly_ranked_outlier_percentage': float(highly_ranked_outlier_percentage),  # Percentage of extremely popular companies
        'lowly_ranked_outlier_count': lowly_ranked_outlier_count,  # Number of extremely unpopular companies
        'lowly_ranked_outlier_percentage': float(lowly_ranked_outlier_percentage),  # Percentage of extremely unpopular companies
        'best_company_avg_ranking': best_company_avg,  # Best company's average ranking
        'worst_company_avg_ranking': worst_company_avg,  # Worst company's average ranking
        'company_ranking_range': company_avg_range,  # Range of company average rankings
        
        # Company performance from composite scoring
        'top_company': company_stats.iloc[0]['Company'],
        'top_company_score': float(company_stats.iloc[0]['Composite Score']),
        'second_company': company_stats.iloc[1]['Company'],
        'second_company_score': float(company_stats.iloc[1]['Composite Score']),
        'third_company': company_stats.iloc[2]['Company'],
        'third_company_score': float(company_stats.iloc[2]['Composite Score']),
        'most_included_company': most_included_company,
        'most_included_count': most_included_count,
        'company_score_range': float(company_stats.iloc[0]['Composite Score'] - company_stats.iloc[-1]['Composite Score']),
        
        # Basic assignment counts
        'total_rankings_given': sum(len(rankings) for rankings in company_ranking_stats),
        'total_unranked_assignments': len(main_df) * len(company_columns) - sum(len(rankings) for rankings in company_ranking_stats)
    }
    
    return input_summary


def collect_algorithm_statistics(student_groups_df: pd.DataFrame, num_students: int, num_companies: int, algorithm_name: str) -> dict:
    """Optimized statistics collection using vectorized operations"""
    
    # Pre-calculate the column structure
    num_columns = ceil(num_students / num_companies)
    
    # Extract all rank data at once using vectorized operations
    rank_columns = [f"Student {i+1} Rank" for i in range(num_columns)]
    rank_data = []
    
    for col in rank_columns:
        if col in student_groups_df.columns:
            # Use dropna() and convert to numeric efficiently
            col_data = pd.to_numeric(student_groups_df[col], errors='coerce').dropna()
            rank_data.extend(col_data.tolist())
    
    # Convert to numpy array for faster operations
    ranks_array = np.array(rank_data)
    
    # Calculate statistics using vectorized operations
    if len(ranks_array) > 0:
        mean_ranking = np.mean(ranks_array)
        
        # Count ranks using bincount (much faster than loops)
        rank_counts = np.bincount(ranks_array.astype(int), minlength=7)[1:7]  # Skip index 0, use 1-6
        total_assignments = len(ranks_array)
        
        # Calculate both raw counts and percentages
        rank_data_dict = {}
        for rank in range(1, 7):
            rank_data_dict[f'students_got_choice_{rank}_count'] = int(rank_counts[rank-1])
            rank_data_dict[f'students_got_choice_{rank}_percent'] = (rank_counts[rank-1] / total_assignments * 100)
        
        # Satisfaction rates for different thresholds
        satisfied_students_top3 = np.sum(rank_counts[:3])  # Ranks 1-3
        satisfied_students_top4 = np.sum(rank_counts[:4])  # Ranks 1-4
        satisfied_students_top5 = np.sum(rank_counts[:5])  # Ranks 1-5
        
        satisfaction_rate_top3 = (satisfied_students_top3 / total_assignments * 100)
        satisfaction_rate_top4 = (satisfied_students_top4 / total_assignments * 100)
        satisfaction_rate_top5 = (satisfied_students_top5 / total_assignments * 100)
        
        # Additional statistical measures
        std_ranking = np.std(ranks_array)
        median_ranking = np.median(ranks_array)
        q1 = np.percentile(ranks_array, 25)
        q3 = np.percentile(ranks_array, 75)
        iqr = q3 - q1
    else:
        mean_ranking = 0
        rank_data_dict = {}
        for rank in range(1, 7):
            rank_data_dict[f'students_got_choice_{rank}_count'] = 0
            rank_data_dict[f'students_got_choice_{rank}_percent'] = 0
        satisfaction_rate_top3 = 0
        satisfaction_rate_top4 = 0
        satisfaction_rate_top5 = 0
        std_ranking = 0
        median_ranking = 0
        iqr = 0
    
    return {
        'algorithm': algorithm_name,
        'avg_student_ranking': mean_ranking,
        'std_student_ranking': std_ranking,
        'median_student_ranking': median_ranking,
        'iqr_student_ranking': iqr,
        'student_satisfaction_percent': satisfaction_rate_top3,  # Keep original name for backward compatibility
        'student_satisfaction_top4_percent': satisfaction_rate_top4,
        'student_satisfaction_top5_percent': satisfaction_rate_top5,
        **rank_data_dict
    }


def get_company_statistics(label: str, value: pd.Series) -> list:
    """Optimized company statistics calculation"""
    # Use vectorized operations instead of loops
    valid_rankings = value.dropna()
    valid_rankings = valid_rankings[valid_rankings <= 5]
    
    if len(valid_rankings) == 0:
        return [label] + [0] * 5 + [0, 0, 0, 0]
    
    # Use numpy bincount for efficient counting
    rank_counts = np.bincount(valid_rankings.astype(int), minlength=6)[1:6]  # Get counts for ranks 1-5
    total_students_who_ranked = len(valid_rankings)
    
    # Vectorized rank score calculation
    weights = np.array([5, 4, 3, 2, 1])
    rank_score = np.sum(rank_counts * weights)
    
    adjusted_score = rank_score / total_students_who_ranked if total_students_who_ranked > 0 else 0
    
    alpha = 0.75
    composite_score = alpha * rank_score + (1 - alpha) * adjusted_score
    
    return [label] + rank_counts.tolist() + [total_students_who_ranked, rank_score, adjusted_score, composite_score]


def get_ranked_companies(df: pd.DataFrame) -> pd.DataFrame:
    """Optimized company ranking using vectorized operations"""
    company_columns = [col for col in df.columns if col != 'Student']
    
    # Pre-allocate result arrays for better performance
    results = []
    
    for company in company_columns:
        stats = get_company_statistics(company, df[company])
        results.append(stats)
    
    # Create DataFrame more efficiently
    columns = ['Company'] + [f'Rank {i+1}' for i in range(5)] + ['Total Students', 'Rank Score', 'Adjusted Score', 'Composite Score']
    ranked_df = pd.DataFrame(results, columns=columns)
    
    return ranked_df


def get_top_companies(df: pd.DataFrame, num_companies: int) -> list:
    """Optimized top company selection"""
    if len(df) <= num_companies:
        return df['Company'].tolist()
    
    # Get the threshold company's statistics
    threshold_row = df.iloc[num_companies - 1]
    threshold_stats = [
        threshold_row['Rank 1'], threshold_row['Rank 2'], threshold_row['Rank 3'],
        threshold_row['Rank 4'], threshold_row['Rank 5'], threshold_row['Total Students'],
        threshold_row['Rank Score'], threshold_row['Adjusted Score'], threshold_row['Composite Score']
    ]
    
    # Find all companies with the same stats as threshold
    tied_mask = (
        (df['Rank 1'] == threshold_stats[0]) &
        (df['Rank 2'] == threshold_stats[1]) &
        (df['Rank 3'] == threshold_stats[2]) &
        (df['Rank 4'] == threshold_stats[3]) &
        (df['Rank 5'] == threshold_stats[4]) &
        (df['Total Students'] == threshold_stats[5]) &
        (df['Rank Score'] == threshold_stats[6]) &
        (df['Adjusted Score'] == threshold_stats[7]) &
        (df['Composite Score'] == threshold_stats[8])
    )
    
    tied_indices = df[tied_mask].index.tolist()
    
    if len(tied_indices) <= 1:
        return df.head(num_companies)['Company'].tolist()
    
    # Handle ties by random selection
    first_tied_index = min(tied_indices)
    num_to_select = num_companies - first_tied_index
    
    selected_indices = np.random.choice(tied_indices, size=min(num_to_select, len(tied_indices)), replace=False)
    
    # Combine non-tied companies with randomly selected tied companies
    final_indices = list(range(first_tied_index)) + sorted(selected_indices)
    
    return df.iloc[final_indices]['Company'].tolist()



def get_rank_first_student_groups(mdf: pd.DataFrame, ttdf: pd.DataFrame, num_students: int, suppress_terminal_output: bool, proposed_companies: dict) -> pd.DataFrame:
    group_buckets = []
    student_groups_list = []
    num_companies = ttdf.shape[0]
    for i in range(num_companies):
        num_slots = ceil(num_students / (num_companies - i))
        group_buckets.append(num_slots)
        num_students -= num_slots
        student_groups_list.append({ttdf['Company'].iloc[i]: []})
        for k in range(num_slots):
            student_groups_list[i][ttdf['Company'].iloc[i]].append([-1, 'NULL', 100, 0, False])
            student_groups_list[i]['Full'] = False

    group_buckets.sort()
    max_group_size = group_buckets[-1]
    # Create columns for the student_groups_df
    student_groups_columns = ['Company']
    for j in range(group_buckets[-1]):
        student_groups_columns.append(f"Student {j+1}")
        student_groups_columns.append(f"Student {j+1} Rank")

    student_groups_df = pd.DataFrame(columns=student_groups_columns)

    student_groups_df_rows = add_students_to_group_by_rank(mdf, student_groups_list, max_group_size, proposed_companies)

    for j in range(len(student_groups_df_rows)):
        student_groups_df.loc[j] = student_groups_df_rows[j]
        if not suppress_terminal_output:
            print(f'{Colors.OKCYAN}{student_groups_df_rows[j][0]}')
            for k in range(max_group_size):
                index = 2*k
                if student_groups_df_rows[j][index+1] == None:
                    continue
            print(f'{Colors.OKGREEN}{student_groups_df_rows[j][index+1]} - {student_groups_df_rows[j][index+2]}')
            print(f'{Colors.ENDC}')
        
    return student_groups_df


def add_students_to_group_by_rank(mdf: pd.DataFrame, student_groups_list: list, max_group_size: int, proposed_companies: dict) -> list:
    for current_rank in range(1, 7):
        for i in range(len(student_groups_list)):
            current_company = None
            for key in student_groups_list[i].keys():
                if key == 'Full':
                    continue
                current_company = key
                break
                
            # Skip if no company found or group is already full
            if current_company is None or student_groups_list[i].get('Full', False):
                continue
            
            remaining_rank_averages = get_remaining_rank_averages(mdf, current_company)

            for index, data in mdf[['Student', current_company]].iterrows():
                current_student = [index, data.iloc[0], data.iloc[1], remaining_rank_averages[data.iloc[0]], False]
                if current_student[2] == current_rank:
                    force_in = False
                    if current_rank == 1:
                        if proposed_companies[current_student[1]] == current_company:
                            force_in = True
                    for j in range(len(student_groups_list[i][current_company])):
                        swap = False
                        if force_in:
                            swap = True
                        elif student_groups_list[i][current_company][j][0] == -1:
                            swap = True
                        elif current_student[2] == student_groups_list[i][current_company][j][2] and current_student[3] > student_groups_list[i][current_company][j][3]:
                            swap = True
                        
                        if swap:
                            student_groups_list[i][current_company].pop(j)
                            student_groups_list[i][current_company].append(current_student)
                            break
            rows_to_remove = []
            is_full = False
            count = 0
            for student in student_groups_list[i][current_company]:
                if student[0] != -1:
                    count += 1
                    if student[4] == False:
                        rows_to_remove.append(student[0])
                        student[4] = True

            if count == len(student_groups_list[i][current_company]):
                is_full = True

            if is_full:
                student_groups_list[i]['Full'] = True
                mdf.drop(columns=current_company, inplace=True)
            
            mdf.drop(rows_to_remove, inplace=True)
            mdf.reset_index(drop=True, inplace=True)

    student_group_rows = []
    for n in range(len(student_groups_list)):
        for key in student_groups_list[n].keys():
            if key == 'Full':
                continue
            company_name = key
            students = [company_name]
        for student in student_groups_list[n][company_name]:
            students.append(student[1])
            students.append(student[2])
        if len(student_groups_list[n][company_name]) < max_group_size:
            diff = max_group_size - len(student_groups_list[n][company_name])
            for _ in range(diff):
                students.append(None)
                students.append(None)
        student_group_rows.append(students)
    return student_group_rows


def get_best_first_student_groups(mdf: pd.DataFrame, ttdf: pd.DataFrame, num_students: int, suppress_terminal_output: bool, proposed_companies: dict) -> pd.DataFrame:
    group_buckets = []
    student_groups_list = []
    num_companies = ttdf.shape[0]
    for i in range(num_companies):
        num_slots = ceil(num_students / (num_companies - i))
        group_buckets.append(num_slots)
        num_students -= num_slots
        student_groups_list.append({ttdf['Company'].iloc[i]: []})
        for k in range(num_slots):
            student_groups_list[i][ttdf['Company'].iloc[i]].append([-1, 'NULL', 100, 0, False]) # [Index, Name, Rank, Remaining Average, Selected Flag]
            student_groups_list[i]['Full'] = False

    group_buckets.sort()
    max_group_size = group_buckets[-1]
    # Create columns for the student_groups_df
    student_groups_columns = ['Company']
    for j in range(group_buckets[-1]):
        student_groups_columns.append(f"Student {j+1}")
        student_groups_columns.append(f"Student {j+1} Rank")

    student_groups_df = pd.DataFrame(columns=student_groups_columns)

    student_groups_df_rows = make_best_first_student_rows(mdf, student_groups_list, max_group_size, proposed_companies)

    for j in range(len(student_groups_df_rows)):
        student_groups_df.loc[j] = student_groups_df_rows[j]
        if not suppress_terminal_output:
            print(f'{Colors.OKCYAN}{student_groups_df_rows[j][0]}')
            for k in range(max_group_size):
                index = 2*k
                if student_groups_df_rows[j][index+1] == None:
                    continue
                print(f'{Colors.OKGREEN}{student_groups_df_rows[j][index+1]} - {student_groups_df_rows[j][index+2]}')
            print(f'{Colors.ENDC}')
        
    return student_groups_df


def make_best_first_student_rows(mdf: pd.DataFrame, student_groups_list: list, max_group_size: int, proposed_companies: dict) -> list:
    full_companies = 0
    all_full = False
    while not all_full:
        for i in range(len(student_groups_list)):
            current_company = None
            for key in student_groups_list[i].keys():
                if key == 'Full':
                    continue
                current_company = key
                break
            
            # Skip if no company found or group is already full
            if current_company is None or student_groups_list[i].get('Full', False):
                continue
            
            remaining_rank_averages = get_remaining_rank_averages(mdf, current_company)
            
            best_student = [-1, 'NULL', 100, 0, False]
            for index, data in mdf[['Student', current_company]].iterrows():
                current_student = [index, data.iloc[0], data.iloc[1], remaining_rank_averages[data.iloc[0]], False]
                if current_student[2] == 1 and proposed_companies[current_student[1]] == current_company:
                    best_student = current_student
                    break
                elif current_student[2] <= best_student[2] and current_student[3] > best_student[3]:
                    best_student = current_student
                    continue
                else:
                    continue

            for j in range(len(student_groups_list[i][current_company])):
                if student_groups_list[i][current_company][j][0] == -1:
                    student_groups_list[i][current_company].pop(j)
                    student_groups_list[i][current_company].append(best_student)
                    break
            
            # Removal Logic for selected students, and Companies (If they're full)
            rows_to_remove = []
            is_full = False
            count = 0
            for student in student_groups_list[i][current_company]:
                if student[0] != -1:
                    count += 1
                    if student[4] == False:
                        rows_to_remove.append(student[0])
                        student[4] = True

            if count == len(student_groups_list[i][current_company]):
                is_full = True
                full_companies += 1
                if full_companies == len(student_groups_list):
                    all_full = True

            if is_full:
                student_groups_list[i]['Full'] = True
                mdf.drop(columns=current_company, inplace=True)
            
            mdf.drop(rows_to_remove, inplace=True)
            mdf.reset_index(drop=True, inplace=True)
            if all_full:
                break

    student_group_rows = []
    for n in range(len(student_groups_list)):
        for key in student_groups_list[n].keys():
            if key == 'Full':
                continue
            company_name = key
            students = [company_name]
        for student in student_groups_list[n][company_name]:
            students.append(student[1])
            students.append(student[2])
        if len(student_groups_list[n][company_name]) < max_group_size:
            diff = max_group_size - len(student_groups_list[n][company_name])
            for _ in range(diff):
                students.append(None)
                students.append(None)
        student_group_rows.append(students)
    
    
    return student_group_rows
            

def get_student_groups(mdf: pd.DataFrame, ttdf: pd.DataFrame, num_students: int, suppress_terminal_output: bool, proposed_companies: dict) -> pd.DataFrame:
    # First thing we should do is create the stucture to hold the students for the final group selection
    group_buckets = []
    num_companies = ttdf.shape[0]
    for i in range(num_companies):
        num_slots = ceil(num_students / (num_companies - i))
        group_buckets.append(num_slots)
        num_students -= num_slots

    group_buckets.sort()
    max_group_size = group_buckets[-1]
    # Create columns for the student_groups_df
    student_groups_columns = ['Company']
    for j in range(group_buckets[-1]):
        student_groups_columns.append(f"Student {j+1}")
        student_groups_columns.append(f"Student {j+1} Rank")

    student_groups_df = pd.DataFrame(columns=student_groups_columns)

    round_num = 1
    for i in range(num_companies-1, -1, -1):
        # Make a row that contains the assigned student group, and add it to the returned dataframe
        student_group = make_student_group(mdf, ttdf['Company'].iloc[i], group_buckets[(num_companies-1)-i], max_group_size, proposed_companies)
        student_groups_df.loc[i] = student_group[0]

        if not suppress_terminal_output:
            print(f'{Colors.OKBLUE}Round {round_num} Student Selection for {student_group[0][0]}{Colors.ENDC}')
            print(f'{Colors.HEADER}-------------------------------------------------------------------------------------------')
            for j in range(len(student_group[1])):
                index = 2*j
                print(f'{Colors.OKGREEN}{student_group[0][index+1]} - {student_group[0][index+2]}{Colors.ENDC}')
            print(f'{Colors.HEADER}-------------------------------------------------------------------------------------------{Colors.ENDC}\n')

        round_num += 1

        # Remove the company from mdf
        mdf.drop(columns=ttdf['Company'].iloc[i], inplace=True)

        # student_group[1] will be a list that contains the indicies of the students to be removed from mdf
        mdf.drop(student_group[1], inplace=True)

        # Reset mdf index
        mdf.reset_index(drop=True, inplace=True)

    return student_groups_df


def make_student_group(mdf: pd.DataFrame, current_company: str, num_slots: int, max_group_size: int, proposed_companies: dict) -> set[list, list]:
    # Here will be the place where we check some data stucture for the current_company proposer.
    # If they're found, we need to make sure that they get selected first, and are not eligble for
    # removal

    selected_students_row_data = [current_company]
    selected_students_index = []

    # Get remaining rank average for every student in mdf
    remaining_rank_averages = get_remaining_rank_averages(mdf, current_company)
    
    # Create empty student group
    student_group = [[-1, 'NULL', 100, 0] for _ in range(num_slots)]
    max_rank = 100

    # Iterate through mdf and select company group
    for index, data in mdf[['Student', current_company]].iterrows():
        current_student = [index, data.iloc[0], data.iloc[1], remaining_rank_averages[data.iloc[0]]]
        # if current_student[2] <= max_rank or not pd.isna(current_student[2]):
        if current_student[2] <= max_rank:
            for j in range(len(student_group)):
                if student_group[j][2] == max_rank:
                    swap = False
                    if current_student[2] == 1 and proposed_companies[current_student[1]] == current_company:
                        swap = True
                    elif current_student[2] == student_group[j][2] and current_student[3] > student_group[j][3]:
                        swap = True
                    elif current_student[2] < student_group[j][2]:
                        swap = True
                    
                    if swap:
                        student_group.pop(j)
                        student_group.append(current_student)
                        max_rank = get_max_student_rank(student_group)
                        break

    for i in range(len(student_group)):
        selected_students_row_data.append(student_group[i][1])
        selected_students_row_data.append(student_group[i][2])
        if student_group[i][0] != -1:
            selected_students_index.append(student_group[i][0])

    for _ in range(max_group_size - num_slots):
        selected_students_row_data.append(None)
        selected_students_row_data.append(None)

    return (selected_students_row_data, selected_students_index)


def get_remaining_rank_averages(mdf: pd.DataFrame, current_company: str) -> dict:
    student_dict = {}
    current_company_index = mdf.columns.get_loc(current_company)
    for index, data in mdf.iterrows():
        remaining_average = 0
        rank_sum = 0
        count = 0
        for i in range(1, len(data)):
            db = data.iloc[i]
            if i == current_company_index or pd.isna(data.iloc[i]):
                continue
            rank_sum += data.iloc[i]
            count += 1
        
        # Prevent division by zero
        if count > 0:
            remaining_average = rank_sum / count
        else:
            remaining_average = 3.5  # Default middle rank average if no other companies
        
        student_dict[data['Student']] = remaining_average

    return student_dict


def get_max_student_rank(student_group: list) -> int:
    max = 0
    for i in range(len(student_group)):
        if student_group[i][2] > max:
            max = student_group[i][2]
    return max


def get_mean_ranking(sdf: pd.DataFrame, num_students: int, num_companies: int) -> float:
    """Optimized mean ranking calculation"""
    num_columns = ceil(num_students / num_companies)
    
    # Get all rank columns
    rank_columns = [f"Student {i+1} Rank" for i in range(num_columns)]
    
    # Extract all ranks efficiently
    all_ranks = []
    for col in rank_columns:
        if col in sdf.columns:
            ranks = pd.to_numeric(sdf[col], errors='coerce').dropna()
            all_ranks.extend(ranks.tolist())
    
    if all_ranks:
        return round(np.mean(all_ranks), 4)
    return 0.0


def main():
    # Create argument parser and parse arguments
    parser = argparse.ArgumentParser("Ranker is a module for running statistical analysis on student-company assignment algorithms")
    
    # Trial configuration
    parser.add_argument("--trials", type=int, default=1, help="Number of trials to run (default: 1, max: 1000)")
    parser.add_argument("--students", type=int, default=30, help="Number of students per trial (default: 30)")
    
    # Company configuration
    parser.add_argument("--total_companies", type=int, default=20, 
                       help="Total companies in pool for ranking (default: 20)")
    parser.add_argument("--selected_companies", type=int, default=10,
                       help="Number of top companies selected for assignment (default: 10)")
    
    parser.add_argument(
        "--selection",
        choices=["ranked", "criticality"],
        default="ranked",
        help="Company selection method (default: ranked)"
    )

    parser.add_argument(
        "--dom",
        type=int,
        default=0,
        help="Run Dual Outlier Matching (DOM) Phase -1 and stop when this many companies remain (0 = disabled)"
    )


    # Algorithm selection
    parser.add_argument("--algorithms", nargs='+', type=int, choices=[0, 1, 2, 3], default=[3],
 
                       help="Algorithms to test: 0=Fill First, 1=Rank First, 2=Best First (default: all)")
    
    # Output configuration
    parser.add_argument("--output_file", type=str, default="algorithm_statistics.csv", 
                       help="Output CSV file name (default: algorithm_statistics.csv)")
    parser.add_argument("--save_input_data", action="store_true", 
                       help="Save generated input data to CSV files for inspection")
    parser.add_argument("--seed", type=int, default=None, 
                       help="Random seed for reproducible results (default: time-based)")
    parser.add_argument("--suppress_terminal_output", action="store_true", 
                       help="Suppress detailed terminal output during trials")
    parser.add_argument("--no_progress_bar", action="store_true", 
                       help="Disable the progress bar")
    parser.add_argument("--progress_interval", type=int, default=10, 
                       help="Show progress every N trials (default: 10)")
    
    args = parser.parse_args()
    
    # Validate company parameters
    if args.selected_companies > args.total_companies:
        return print(f"Error: selected_companies ({args.selected_companies}) cannot exceed total_companies ({args.total_companies})")
    
    if args.selected_companies < 1:
        return print("Error: selected_companies must be at least 1")
    
    if args.total_companies < 1:
        return print("Error: total_companies must be at least 1")
    
    # Set random seeds after parsing arguments
    if args.seed is not None:
        seed = args.seed
        print(f"Using user-specified random seed: {seed}")
    else:
        import time
        seed = int(time.time()) % 2**32  # Time-based seed for varied data across runs
        print(f"Using time-based random seed: {seed}")
    
    np.random.seed(seed)
    random.seed(seed)
    
    # Validate arguments
    if args.trials > 1000:
        return print("Error: Maximum number of trials is 1000")
    
    if args.trials < 1:
        return print("Error: Number of trials must be at least 1")
    
    # Run optimized trial-based mode
    return run_trial_mode(args)

def check_structural_viability(main_df: pd.DataFrame, top_companies: list) -> bool:
    """
    A trial is structurally viable if every student has at least
    one ranked choice (1–5) among the selected companies.
    """
    company_columns = [col for col in main_df.columns if col != 'Student']

    for _, row in main_df.iterrows():
        has_valid_option = False

        for company in top_companies:
            if company in company_columns:
                rank_value = row[company]
                if pd.notna(rank_value) and rank_value <= 5:
                    has_valid_option = True
                    break

        if not has_valid_option:
            return False

    return True

def get_top_companies_criticality(main_df: pd.DataFrame,
                                  ranked_companies_df: pd.DataFrame,
                                  K: int) -> list:
    """
    Full Phase 1 Criticality-Based Company Reduction (Capacity-Aware)

    Steps:
    - Compute m = floor(N / K)
    - Remove companies with Demand < m
    - Iteratively remove exactly one company at a time
    - Hard veto: no student may drop to 0 options
    - Lexicographic minimization:
        1) Backup Criticality
        2) Total Criticality Shift
    """

    import math

    N = len(main_df)
    m = math.floor(N / K)

    remaining_companies = ranked_companies_df['Company'].tolist()

    # --- Helper: count valid top-5 options per student ---
    def student_option_counts(df, companies):
        counts = {}
        for _, row in df.iterrows():
            count = 0
            for c in companies:
                rank = row[c]
                if pd.notna(rank) and rank <= 5:
                    count += 1
            counts[row['Student']] = count
        return counts

    # --- Step 1: Hard filter (Demand < m) ---
    demand = {c: (main_df[c] <= 5).sum() for c in remaining_companies}
    remaining_companies = [c for c in remaining_companies if demand[c] >= m]

    # If hard filter already reduces below K, return what remains
    if len(remaining_companies) <= K:
        return remaining_companies

    # --- Step 2: Iterative criticality removal ---
    while len(remaining_companies) > K:

        current_counts = student_option_counts(main_df, remaining_companies)
        removable_candidates = []

        for company in remaining_companies:

            test_companies = [c for c in remaining_companies if c != company]
            test_counts = student_option_counts(main_df, test_companies)

            # --- Hard veto ---
            zero_created = any(test_counts[s] == 0 for s in test_counts)
            if zero_created:
                continue

            # --- Backup Criticality ---
            backup_criticality = 0
            for s in test_counts:
                if current_counts[s] >= 2 and test_counts[s] == 1:
                    backup_criticality += 1

            # --- Total Criticality Shift ---
            total_shift = sum(current_counts[s] - test_counts[s]
                              for s in test_counts)

            removable_candidates.append(
                (backup_criticality, total_shift, company)
            )

        if not removable_candidates:
            break

        removable_candidates.sort()
        _, _, company_to_remove = removable_candidates[0]
        remaining_companies.remove(company_to_remove)

    return remaining_companies


def run_trial_mode(args):
    """Run multiple trials with synthetic data and collect statistics - OPTIMIZED"""
    print(f"{Colors.OKBLUE}Running {args.trials} trial(s) with {args.students} students{Colors.ENDC}")
    print(f"Company pool: {args.total_companies} total → {args.selected_companies} selected for assignment")
    print(f"Selection rate: {args.selected_companies/args.total_companies*100:.1f}% (competitive selection)")
    print(f"Algorithms to test: {[['Fill First', 'Rank First', 'Best First', 'Fragility Mirror'][alg] for alg in args.algorithms]}")

    print(f"Output file: {args.output_file}")
    print()
    
    all_results = []
    input_summaries = []  # Collect input data summaries
    algorithm_functions = {
        0: ('Fill First', get_student_groups),
        1: ('Rank First', get_rank_first_student_groups), 
        2: ('Best First', get_best_first_student_groups),
        3: ('Fragility Mirror', get_fragility_mirror_student_groups)
    }
    
    # Create progress bar if tqdm is available and not disabled
    if TQDM_AVAILABLE and not args.no_progress_bar:
        progress_bar = tqdm(range(args.trials), desc="Processing trials", unit="trial")
    else:
        progress_bar = range(args.trials)
    
    for trial in progress_bar:
        # Update progress bar description if available
        if TQDM_AVAILABLE and not args.no_progress_bar:
            progress_bar.set_description(f"Trial {trial + 1}/{args.trials}")
        elif (trial + 1) % args.progress_interval == 0:
            print(f"{Colors.OKCYAN}Completed {trial + 1}/{args.trials} trials{Colors.ENDC}")
        
        # Generate synthetic data for this trial using optimized function
        main_df = generate_synthetic_data(args.students, args.total_companies)
        proposed_companies = generate_proposed_companies(main_df)
        
        # preserve the original
        original_trial_df = main_df.copy()

        # Run company ranking and selection using optimized functions
        ranked_companies_df = get_ranked_companies(main_df)
        ranked_companies_df = ranked_companies_df.sort_values(
            by=['Composite Score', 'Rank 1', 'Rank 2', 'Rank 3', 'Rank 4'], 
            ascending=[False, False, False, False, False]
        ).reset_index(drop=True)
        
        # Collect input data summary if requested
        if args.save_input_data:
            input_summary = save_trial_input_data(main_df, proposed_companies, ranked_companies_df, trial + 1, args)
            input_summaries.append(input_summary)
        
        # Run DOM routine as preplacement of outlier students into outlier companies
        if args.dom > 0:

            company_index_map = {
                company: idx
                for idx, company in enumerate(ranked_companies_df['Company'].tolist())
            }

            locked_assignments, remaining_students_df, remaining_companies = run_dom_preprocess(
                main_df,
                args.selected_companies,
                args.dom,
                company_index_map
            )

            main_df = remaining_students_df.copy()

        else:
            locked_assignments = []

        # Select companies using a selection algorthim 
        if args.selection == "ranked":
            top_companies = get_top_companies(
                ranked_companies_df,
                args.selected_companies
            )
        else:
            top_companies = get_top_companies_criticality(
                main_df,
                ranked_companies_df,
                args.selected_companies
            )


        # Structural viability check (before placement)
        structurally_viable = check_structural_viability(main_df, top_companies)

        
        # Filter to selected companies
        filtered_df = ranked_companies_df[ranked_companies_df['Company'].isin(top_companies)].reset_index(drop=True)
        
        # Run each selected algorithm
        trial_results = {
            'trial': trial + 1,
            'structurally_viable': structurally_viable
        }

       
        for algorithm_id in args.algorithms:
            algorithm_name, algorithm_function = algorithm_functions[algorithm_id]
            
            # Create a copy of the dataframe for this algorithm
            df_copy = main_df.copy()
            
            # Run the algorithm
            student_groups_df = algorithm_function(
                df_copy,
                filtered_df,
                len(df_copy),   # ← THIS IS THE FIX
                True,
                proposed_companies
            )


            # --- MERGE DOM ASSIGNMENTS BACK IN ---

            if locked_assignments:

                # Determine max group size from Phase 0 output
                rank_columns = [col for col in student_groups_df.columns if "Student" in col and "Rank" not in col]
                max_group_size = len(rank_columns)

                dom_rows = []

                # Group DOM assignments by company
                dom_dict = {}
                for student_index, company in locked_assignments:
                    student_name = original_trial_df.iloc[student_index]['Student']
                    student_rank = original_trial_df.iloc[student_index][company]
                    dom_dict.setdefault(company, []).append((student_name, student_rank))

                # Build rows matching the student_groups_df structure
                for company, students in dom_dict.items():
                    row = [company]

                    for i in range(max_group_size):
                        if i < len(students):
                            row.append(students[i][0])
                            row.append(students[i][1])
                        else:
                            row.append(None)
                            row.append(None)

                    dom_rows.append(row)

                dom_df = pd.DataFrame(dom_rows, columns=student_groups_df.columns)

                # Merge DOM + Phase 0
                student_groups_df = pd.concat([dom_df, student_groups_df], ignore_index=True)

            # Collect statistics using optimized function
            stats = collect_algorithm_statistics(student_groups_df, args.students, args.selected_companies, algorithm_name)
            
            # Add algorithm-specific prefix to column names with descriptive prefixes
            alg_prefix = ['fill_first', 'rank_first', 'best_first', 'fragility_mirror'][algorithm_id]

            for key, value in stats.items():
                if key != 'algorithm':
                    trial_results[f'{alg_prefix}_{key}'] = value
        
        all_results.append(trial_results)
    

    # Create results DataFrame and save
    results_df = pd.DataFrame(all_results)
   
    results_df.to_csv(args.output_file, index=False)

    # Structural viability summary
    if 'structurally_viable' in results_df.columns:
        viable_rate = results_df['structurally_viable'].mean() * 100
        print(f"\nStructural Viability Rate: {viable_rate:.2f}% of trials")

 
    # Save input data summaries if requested
    if args.save_input_data and input_summaries:
        input_file = args.output_file.replace('.csv', '_input_summary.csv')
        input_df = pd.DataFrame(input_summaries)
        input_df.to_csv(input_file, index=False)
        print(f"{Colors.OKGREEN}Input data summary saved to {input_file}{Colors.ENDC}")
    
    print(f"\n{Colors.OKGREEN}Completed all {args.trials} trials!{Colors.ENDC}")
    print(f"Results saved to {args.output_file}")
    
    # Print summary statistics
    if not args.suppress_terminal_output:
        print(f"\n{Colors.OKBLUE}Summary Statistics:{Colors.ENDC}")
        print("=" * 60)
        
        for algorithm_id in args.algorithms:
            alg_prefix = ['fill_first', 'rank_first', 'best_first', 'fragility_mirror'][algorithm_id]
            alg_name = ['Fill First', 'Rank First', 'Best First', 'Fragility Mirror'][algorithm_id]
 
            mean_col = f'{alg_prefix}_avg_student_ranking'
            satisfaction_col = f'{alg_prefix}_student_satisfaction_percent'
            satisfaction_top4_col = f'{alg_prefix}_student_satisfaction_top4_percent'
            satisfaction_top5_col = f'{alg_prefix}_student_satisfaction_top5_percent'
            
            if mean_col in results_df.columns:
                mean_avg = results_df[mean_col].mean()
                mean_std = results_df[mean_col].std()
                satisfaction_avg = results_df[satisfaction_col].mean()
                satisfaction_std = results_df[satisfaction_col].std()
                satisfaction_top4_avg = results_df[satisfaction_top4_col].mean()
                satisfaction_top4_std = results_df[satisfaction_top4_col].std()
                satisfaction_top5_avg = results_df[satisfaction_top5_col].mean()
                satisfaction_top5_std = results_df[satisfaction_top5_col].std()
                
                print(f"\n{Colors.WARNING}{alg_name}:{Colors.ENDC}")
                print(f"  Average Student Ranking: {mean_avg:.3f} ± {mean_std:.3f}")
                print(f"  Student Satisfaction (Top-3): {satisfaction_avg:.1f}% ± {satisfaction_std:.1f}%")
                print(f"  Student Satisfaction (Top-4): {satisfaction_top4_avg:.1f}% ± {satisfaction_top4_std:.1f}%")
                print(f"  Student Satisfaction (Top-5): {satisfaction_top5_avg:.1f}% ± {satisfaction_top5_std:.1f}%")
                # Perfect Top-5 placement rate (all students got rank 1-5)
                # Perfect Top-5 placement rate
                choice6_col = f'{alg_prefix}_students_got_choice_6_count'

                perfect_mask = results_df[choice6_col] == 0
                viable_mask = results_df['structurally_viable'] == True

                perfect_total_rate = perfect_mask.mean() * 100

                if viable_mask.sum() > 0:
                    perfect_viable_rate = (
                        (perfect_mask & viable_mask).sum() / viable_mask.sum()
                    ) * 100
                else:
                    perfect_viable_rate = 0.0

                print(f"  Perfect Top-5 Rate (All Trials): {perfect_total_rate:.2f}%")
                print(f"  Perfect Top-5 Rate (Structurally Viable Only): {perfect_viable_rate:.2f}%")





def get_fragility_mirror_student_groups(mdf: pd.DataFrame, ttdf: pd.DataFrame, num_students: int, suppress_terminal_output: bool, proposed_companies: dict) -> pd.DataFrame:
    """
    Fragility Mirror Algorithm (Algorithm 3)

    1. Always select the most fragile student first.
    2. For each possible placement, simulate:
        - Backup fragility increase
        - Total fragility shift
    3. Choose the placement with lowest:
        (backup fragility, total fragility shift, numerical rank)
    4. Recalculate fragility after every placement.
    5. If no viable ranked choice exists, assign lowest numerical rank available.
    """

    # --- Setup ---
    selected_companies = ttdf['Company'].tolist()
    group_buckets = []
    remaining_students = num_students
    num_companies = len(selected_companies)

    for i in range(num_companies):
        num_slots = ceil(remaining_students / (num_companies - i))
        group_buckets.append(num_slots)
        remaining_students -= num_slots

    group_buckets.sort()
    max_group_size = group_buckets[-1]

    student_groups_columns = ['Company']
    for j in range(max_group_size):
        student_groups_columns.append(f"Student {j+1}")
        student_groups_columns.append(f"Student {j+1} Rank")

    student_groups_df = pd.DataFrame(columns=student_groups_columns)

    # Track seats
    seats_remaining = {selected_companies[i]: group_buckets[i] for i in range(num_companies)}

    # Helper to compute fragility
    def compute_fragility(df):
        frag = {}
        for idx, row in df.iterrows():
            count = 0
            for c in selected_companies:
                if c in df.columns:
                    if row[c] <= 6:
                        count += 1
            frag[row['Student']] = count
        return frag

    # --- Placement loop ---
    while len(mdf) > 0:

        fragility = compute_fragility(mdf)

        # Select most fragile student
        min_frag = min(fragility.values())
        fragile_students = [s for s in fragility if fragility[s] == min_frag]
        current_student = fragile_students[0]  # arbitrary among equals

        student_row = mdf[mdf['Student'] == current_student].iloc[0]

        best_option = None
        best_tuple = (float('inf'), float('inf'), float('inf'))

        for company in selected_companies:
            if seats_remaining[company] <= 0:
                continue

            rank_value = student_row.get(company, 6)

            # Simulate removal
            df_copy = mdf.drop(mdf[mdf['Student'] == current_student].index)
            frag_after = compute_fragility(df_copy)

            backup_frag = 0
            total_shift = 0

            for s in frag_after:
                before = fragility.get(s, 0)
                after = frag_after.get(s, 0)
                if before >= 2 and after == 1:
                    backup_frag += 1
                total_shift += (before - after)

            candidate_tuple = (backup_frag, total_shift, rank_value)

            if candidate_tuple < best_tuple:
                best_tuple = candidate_tuple
                best_option = company

        # Fallback if no option
        if best_option is None:
            best_option = selected_companies[0]

        # Assign
        seat_index = group_buckets[selected_companies.index(best_option)] - seats_remaining[best_option]
        if best_option not in student_groups_df['Company'].values:
            row_data = [best_option] + [None]*(2*max_group_size)
            student_groups_df.loc[len(student_groups_df)] = row_data

        row_idx = student_groups_df[student_groups_df['Company'] == best_option].index[0]
        col_student = 1 + 2*seat_index
        col_rank = col_student + 1

        student_groups_df.iloc[row_idx, col_student] = current_student
        student_groups_df.iloc[row_idx, col_rank] = student_row.get(best_option, 6)

        seats_remaining[best_option] -= 1
        mdf = mdf.drop(mdf[mdf['Student'] == current_student].index).reset_index(drop=True)

    return student_groups_df

def run_dom_preprocess(df, selected_companies, dom_stop, company_index_map):

    # --- INITIAL POOLS ---
    unassigned_students = df.copy()
    dom_pool_companies = list(df.columns[1:])  # adjust if needed
    struct_companies_remaining = selected_companies

    locked_assignments = []

    while struct_companies_remaining > dom_stop:

        if struct_companies_remaining <= 0:
            break

        if len(dom_pool_companies) == 0:
            break

        # --- MOVING MIN SEATS (FLOOR) ---
        moving_MinSeats = len(unassigned_students) // struct_companies_remaining

        if moving_MinSeats == 0:
            break

        # --- WEANING ---
        eligible_companies = []

        for c in dom_pool_companies:
            demand = unassigned_students[c].apply(lambda x: 1 if x <= 5 else 0).sum()
            if demand >= moving_MinSeats:
                eligible_companies.append((c, demand))

        if not eligible_companies:
            break

        # --- STEP 1: MIN DEMAND ---
        min_demand = min(d for _, d in eligible_companies)
        demand_ties = [c for c, d in eligible_companies if d == min_demand]

        # --- STEP 2: SIMULATED FILL TIE-BREAK ---
        best_company = None
        best_fragility_score = None

        for c in demand_ties:

            candidates = unassigned_students[unassigned_students[c] <= 5]

            fragility_list = []

            for idx, row in candidates.iterrows():
                remaining_options = sum(
                    1 for comp in dom_pool_companies
                    if row[comp] <= 5
                )
                fragility_list.append((idx, remaining_options, row[c]))

            fragility_list.sort(key=lambda x: (x[1], -x[2]))

            selected = fragility_list[:moving_MinSeats]

            fragility_score = sum(x[1] for x in selected)

            if best_fragility_score is None or fragility_score < best_fragility_score:
                best_fragility_score = fragility_score
                best_company = c

            elif fragility_score == best_fragility_score:
                if company_index_map[c] < company_index_map[best_company]:
                    best_company = c

        if best_company is None:
            break

        # --- LOCK COMPANY ---
        candidates = unassigned_students[unassigned_students[best_company] <= 5]

        fragility_list = []

        for idx, row in candidates.iterrows():
            remaining_options = sum(
                1 for comp in dom_pool_companies
                if row[comp] <= 5
            )
            fragility_list.append((idx, remaining_options, row[best_company]))

        fragility_list.sort(key=lambda x: (x[1], -x[2]))

        selected_students = [x[0] for x in fragility_list[:moving_MinSeats]]

        # assign and lock
        for s in selected_students:
            locked_assignments.append((s, best_company))

        unassigned_students = unassigned_students.drop(selected_students)
        dom_pool_companies.remove(best_company)

        struct_companies_remaining -= 1

        # Debug Printing
        # print("DOM COMPLETE")
        # print("Locked students:", len(locked_assignments))
        # print("Remaining DOM pool companies:", len(dom_pool_companies))
        # print("Remaining students:", len(unassigned_students))
        # print("Structural companies remaining:", struct_companies_remaining)
        # print("------")

    return locked_assignments, unassigned_students, dom_pool_companies
    

    return main_df, ranked_companies_df, locked_assignments
    

if __name__ == '__main__':
    main()