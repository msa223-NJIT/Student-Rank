import pandas as pd
import numpy as np
from math import ceil
import random
import argparse
from cparser import CParser


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


def get_company_statistics(label: str, value: pd.Series) -> list:
    # Compute statistics for a single company row
    rank_counts = [0, 0, 0, 0, 0]
    total_students_who_ranked = 0

    for rank in value:
        if pd.isna(rank) or rank > 5:
            continue
        else:
            total_students_who_ranked += 1
            rank_counts[int(rank)-1] += 1
    
    rank_score = 5*rank_counts[0] + 4*rank_counts[1] + 3*rank_counts[2] + 2*rank_counts[3] + rank_counts[4]
    adjusted_score = rank_score / total_students_who_ranked
    alpha = 0.75
    composite_score = alpha*rank_score + (1-alpha)*adjusted_score

    row = [label] + rank_counts + [total_students_who_ranked, rank_score, adjusted_score, composite_score]

    return row


def get_ranked_companies(df: pd.DataFrame) -> pd.DataFrame:
    # Create an empty ranked_df that will be returned with all the necessary statistics
    ranked_df_columns = ['Company']
    for i in range(5):
        ranked_df_columns.append(f'Rank {i+1}')
    ranked_df_columns = ranked_df_columns + ['Total Students', 'Rank Score', 'Adjusted Score','Composite Score']
    ranked_df = pd.DataFrame(columns=ranked_df_columns)
    count = 0
    # Calculate all the necessary statistics
    for label, value in df.items():
        if label == "Student":
            continue
        row_statistics = get_company_statistics(label, value)
        ranked_df.loc[count] = row_statistics
        count += 1

    return ranked_df


def get_top_companies(df: pd.DataFrame, num_companies: int) -> list:
    # We only need to check for equality with the tenth company in the list. Since we have already gone through
    # all the other tie breaks, if there's equality, we need to randomly select those that are equal with index 9.
    xth_company_row_data = top_companies_row_data(df.iloc[num_companies-1])
    tied_entries = []
    top_ten_entries = []
    for index, data in df.iterrows():
        row_data = top_companies_row_data(data)
        if row_data == xth_company_row_data:
            tied_entries.append(index)
    
    if len(tied_entries) > 1:
        tied_entries.sort()
        num_to_select = (num_companies - 1) - tied_entries[0]
        selected_companies = np.random.choice(tied_entries, size=(num_to_select + 1), replace=False)
        np.sort(selected_companies)
        selected_companies = list(selected_companies)
    else:
        selected_companies = tied_entries

    for i in range(tied_entries[0]):
        top_ten_entries.append(df.iloc[i]['Company'])

    for index in selected_companies:
        top_ten_entries.append(df.iloc[index]['Company'])

    return top_ten_entries


def top_companies_row_data(s: pd.Series) -> list:
    return [s['Rank 1'], s['Rank 2'], s['Rank 3'], s['Rank 4'], s['Rank 5'], s['Total Students'], s['Rank Score'], s['Adjusted Score'], s['Composite Score']]


def get_rank_first_student_groups(mdf: pd.DataFrame, ttdf: pd.DataFrame, num_students: int, suppress_terminal_output: bool, proposed_companies: dict) -> pd.DataFrame:
    group_buckets = []
    student_groups_list = []
    num_companies = ttdf.shape[0]
    for i in range(num_companies):
        num_slots = ceil(num_students / (num_companies - i))
        group_buckets.append(num_slots)
        num_students -= num_slots
        student_groups_list.append({ttdf.loc[i]: []})
        for k in range(num_slots):
            student_groups_list[i][ttdf.loc[i]].append([-1, 'NULL', 100, 0, False])
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
            for key in student_groups_list[i].keys():
                if key == 'Full':
                    break
                current_company = key
                
            if student_groups_list[i]['Full'] == True:
                continue
            else:
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
        student_groups_list.append({ttdf.loc[i]: []})
        for k in range(num_slots):
            student_groups_list[i][ttdf.loc[i]].append([-1, 'NULL', 100, 0, False]) # [Index, Name, Rank, Remaining Average, Selected Flag]
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
            for key in student_groups_list[i].keys():
                if key == 'Full':
                    break
                current_company = key
            
            if student_groups_list[i]['Full'] == True:
                continue
            else:
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
        student_group = make_student_group(mdf, ttdf.iloc[i], group_buckets[(num_companies-1)-i], max_group_size, proposed_companies)
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
        mdf.drop(columns=ttdf.iloc[i], inplace=True)

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
        for i in range(1, len(data)):
            db = data.iloc[i]
            if i == current_company_index or pd.isna(data.iloc[i]):
                continue
            rank_sum += data.iloc[i]
        remaining_average = rank_sum / (len(data) - 2)
        student_dict[data['Student']] = remaining_average

    return student_dict


def get_max_student_rank(student_group: list) -> int:
    max = 0
    for i in range(len(student_group)):
        if student_group[i][2] > max:
            max = student_group[i][2]
    return max


def get_mean_ranking(sdf: pd.DataFrame, num_students: int, num_companies: int) -> float:
    mean_ranking = 0
    s_sum = 0
    num_columns = ceil(num_students / num_companies)
    for row, data in sdf.iterrows():
        for i in range(1, num_columns + 1):
            index = 2*i
            if data.iloc[index] == None:
                continue
            s_sum += data.iloc[index]

    mean_ranking = round(s_sum / num_students, 4)
    return mean_ranking


def main():
    # Create argument parser and parse arguments
    parser = argparse.ArgumentParser("Ranker is a module for assigning Students into Company Groups")
    parser.add_argument("--file", type=str, required=True, help="Input .csv File Path (Required)")
    parser.add_argument("--students", type=int, required=False, help="Number of students to process. If absent, will default to all students in --file (Optional)")
    parser.add_argument("--companies", type=int, default=10, help="Number of companies to rank")
    parser.add_argument("--output_path", type=str, required=False, default='', help="Path to Output (Optional)")
    parser.add_argument("--suppress_terminal_output", type=bool, default=False, help="Option to suppress terminal output of program")
    parser.add_argument("--rank_first", type=bool, default=False, help="Group selection is done rank-by-rank with remaining average tie-break")
    parser.add_argument("--type", type=int, default=0, choices=[0, 1, 2], required=True, help="Integer which determines what selection method is used. 0 - Fill First (ff), 1 - Rank First (rf), 2 - Best First (bf)")
    args = parser.parse_args()

    input_file = args.file
    if input_file[-4:] != '.csv':
        return print(f"'{input_file}' argument for '--file' is invalid, must be a file with a .csv extension")

    # Make company column list
    # company_columns = [0] + [x for x in range(1, args.companies + 1)]

    try:
    # Read input_file and num_students, and convert the file into our main dataframe
        if args.students:
            num_students = args.students
            c_parser = CParser(input_file)
            main_df = c_parser.make_data_frame(num_students)
            # main_df = pd.read_csv(input_file, usecols=company_columns, nrows=num_students)
        else:
            c_parser = CParser(input_file)
            main_df = c_parser.make_data_frame()
            # main_df = pd.read_csv(input_file, usecols=company_columns)
            num_students = main_df.shape[0]
    except (OSError, FileNotFoundError, pd.errors.ParserError) as e:
        return print(f"Error encountered. Program has terminated.\nError: {e}")
    
    # Take the wide dataframe, and narrow down the companies to the top ten
    # We can first calculate the rank score, adjusted score, and composite score for all input companies
    ranked_companies_df = get_ranked_companies(main_df)
    ranked_companies_df.sort_values(by=['Composite Score', 'Rank 1', 'Rank 2', 'Rank 3', 'Rank 4'], ascending=[False, False, False, False, False], inplace=True)
    ranked_companies_df.reset_index(drop=True, inplace=True)
    if not args.suppress_terminal_output:
        print(f'{Colors.OKBLUE}Rankings of Companies by Composite Score (Descending){Colors.ENDC}')
        print(f'{Colors.HEADER}-------------------------------------------------------------------------------------------')
        print(f'{ranked_companies_df}')
        print(f'-------------------------------------------------------------------------------------------{Colors.ENDC}')

    # Here is where we can provide logic for random tie-breaks, given we've exhausted all other layers and still need it
    top_companies = get_top_companies(ranked_companies_df, args.companies)

    rows_to_remove = []
    for index, data in ranked_companies_df.iterrows():
        if data['Company'] not in top_companies:
            rows_to_remove.append(index)
    
    ranked_companies_df.drop(rows_to_remove, inplace=True)
    ranked_companies_df.reset_index(drop=True, inplace=True)


    if not args.suppress_terminal_output:
        print(f'\n{Colors.OKBLUE}Top {args.companies} Companies (Descending){Colors.ENDC}')
        print(f'{Colors.HEADER}-------------------------------------------------------------------------------------------')
        print(f'{ranked_companies_df}')
        print(f'-------------------------------------------------------------------------------------------{Colors.ENDC}\n')
    
    # Now that we have the top ten companies, we can assign the students
    if args.type == 0:
        student_groups_df = get_student_groups(main_df, ranked_companies_df['Company'], num_students, args.suppress_terminal_output, c_parser.proposed_companies)
        file_name = 'ranker2data_ff.csv'
    elif args.type == 1:
        student_groups_df = get_rank_first_student_groups(main_df, ranked_companies_df['Company'], num_students, args.suppress_terminal_output, c_parser.proposed_companies)
        file_name = 'ranker2data_rf.csv'
    elif args.type == 2:
        student_groups_df = get_best_first_student_groups(main_df, ranked_companies_df['Company'], num_students, args.suppress_terminal_output, c_parser.proposed_companies)
        file_name = 'ranker2data_bf.csv'
    else:
        print("Error: Invalid Choice for Selection Algorithm")
        exit()
        
    
    mean_ranking = get_mean_ranking(student_groups_df, num_students, args.companies)

    if not args.suppress_terminal_output:
        print(f'{Colors.WARNING}Mean Ranking - {mean_ranking}{Colors.ENDC}')
    
    student_groups_df.to_csv(file_name, index=False)
    return


if __name__ == '__main__':
    main()