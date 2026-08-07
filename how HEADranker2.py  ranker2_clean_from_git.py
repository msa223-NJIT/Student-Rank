[1mdiff --git a/ranker2.py b/ranker2.py[m
[1mindex b6d08a4..e08244d 100644[m
[1m--- a/ranker2.py[m
[1m+++ b/ranker2.py[m
[36m@@ -803,7 +803,8 @@[m [mdef main():[m
                        help="Number of top companies selected for assignment (default: 10)")[m
     [m
     # Algorithm selection[m
[31m-    parser.add_argument("--algorithms", nargs='+', type=int, choices=[0, 1, 2], default=[0, 1, 2], [m
[32m+[m[32m    parser.add_argument("--algorithms", nargs='+', type=int, choices=[0, 1, 2, 3], default=[3],[m
[32m+[m[41m [m
                        help="Algorithms to test: 0=Fill First, 1=Rank First, 2=Best First (default: all)")[m
     [m
     # Output configuration[m
[36m@@ -860,7 +861,8 @@[m [mdef run_trial_mode(args):[m
     print(f"{Colors.OKBLUE}Running {args.trials} trial(s) with {args.students} students{Colors.ENDC}")[m
     print(f"Company pool: {args.total_companies} total → {args.selected_companies} selected for assignment")[m
     print(f"Selection rate: {args.selected_companies/args.total_companies*100:.1f}% (competitive selection)")[m
[31m-    print(f"Algorithms to test: {[['Fill First', 'Rank First', 'Best First'][alg] for alg in args.algorithms]}")[m
[32m+[m[32m    print(f"Algorithms to test: {[['Fill First', 'Rank First', 'Best First', 'Fragility Mirror'][alg] for alg in args.algorithms]}")[m
[32m+[m
     print(f"Output file: {args.output_file}")[m
     print()[m
     [m
[36m@@ -869,7 +871,8 @@[m [mdef run_trial_mode(args):[m
     algorithm_functions = {[m
         0: ('Fill First', get_student_groups),[m
         1: ('Rank First', get_rank_first_student_groups), [m
[31m-        2: ('Best First', get_best_first_student_groups)[m
[32m+[m[32m        2: ('Best First', get_best_first_student_groups),[m
[32m+[m[32m        3: ('Fragility Mirror', get_fragility_mirror_student_groups)[m
     }[m
     [m
     # Create progress bar if tqdm is available and not disabled[m
[36m@@ -929,7 +932,8 @@[m [mdef run_trial_mode(args):[m
             stats = collect_algorithm_statistics(student_groups_df, args.students, args.selected_companies, algorithm_name)[m
             [m
             # Add algorithm-specific prefix to column names with descriptive prefixes[m
[31m-            alg_prefix = ['fill_first', 'rank_first', 'best_first'][algorithm_id][m
[32m+[m[32m            alg_prefix = ['fill_first', 'rank_first', 'best_first', 'fragility_mirror'][algorithm_id][m
[32m+[m
             for key, value in stats.items():[m
                 if key != 'algorithm':[m
                     trial_results[f'{alg_prefix}_{key}'] = value[m
[36m@@ -956,9 +960,9 @@[m [mdef run_trial_mode(args):[m
         print("=" * 60)[m
         [m
         for algorithm_id in args.algorithms:[m
[31m-            alg_prefix = ['fill_first', 'rank_first', 'best_first'][algorithm_id][m
[31m-            alg_name = ['Fill First', 'Rank First', 'Best First'][algorithm_id][m
[31m-            [m
[32m+[m[32m            alg_prefix = ['fill_first', 'rank_first', 'best_first', 'fragility_mirror'][algorithm_id][m
[32m+[m[32m            alg_name = ['Fill First', 'Rank First', 'Best First', 'Fragility Mirror'][algorithm_id][m
[32m+[m[41m [m
             mean_col = f'{alg_prefix}_avg_student_ranking'[m
             satisfaction_col = f'{alg_prefix}_student_satisfaction_percent'[m
             satisfaction_top4_col = f'{alg_prefix}_student_satisfaction_top4_percent'[m
[36m@@ -980,6 +984,118 @@[m [mdef run_trial_mode(args):[m
                 print(f"  Student Satisfaction (Top-4): {satisfaction_top4_avg:.1f}% ± {satisfaction_top4_std:.1f}%")[m
                 print(f"  Student Satisfaction (Top-5): {satisfaction_top5_avg:.1f}% ± {satisfaction_top5_std:.1f}%")[m
 [m
[32m+[m[32mdef get_fragility_mirror_student_groups(mdf: pd.DataFrame, ttdf: pd.DataFrame, num_students: int, suppress_terminal_output: bool, proposed_companies: dict) -> pd.DataFrame:[m
[32m+[m[32m    """[m
[32m+[m[32m    Fragility Mirror Algorithm (Algorithm 3)[m
[32m+[m
[32m+[m[32m    1. Always select the most fragile student first.[m
[32m+[m[32m    2. For each possible placement, simulate:[m
[32m+[m[32m        - Backup fragility increase[m
[32m+[m[32m        - Total fragility shift[m
[32m+[m[32m    3. Choose the placement with lowest:[m
[32m+[m[32m        (backup fragility, total fragility shift, numerical rank)[m
[32m+[m[32m    4. Recalculate fragility after every placement.[m
[32m+[m[32m    5. If no viable ranked choice exists, assign lowest numerical rank available.[m
[32m+[m[32m    """[m
[32m+[m
[32m+[m[32m    # --- Setup ---[m
[32m+[m[32m    selected_companies = ttdf['Company'].tolist()[m
[32m+[m[32m    group_buckets = [][m
[32m+[m[32m    remaining_students = num_students[m
[32m+[m[32m    num_companies = len(selected_companies)[m
[32m+[m
[32m+[m[32m    for i in range(num_companies):[m
[32m+[m[32m        num_slots = ceil(remaining_students / (num_companies - i))[m
[32m+[m[32m        group_buckets.append(num_slots)[m
[32m+[m[32m        remaining_students -= num_slots[m
[32m+[m
[32m+[m[32m    group_buckets.sort()[m
[32m+[m[32m    max_group_size = group_buckets[-1][m
[32m+[m
[32m+[m[32m    student_groups_columns = ['Company'][m
[32m+[m[32m    for j in range(max_group_size):[m
[32m+[m[32m        student_groups_columns.append(f"Student {j+1}")[m
[32m+[m[32m        student_groups_columns.append(f"Student {j+1} Rank")[m
[32m+[m
[32m+[m[32m    student_groups_df = pd.DataFrame(columns=student_groups_columns)[m
[32m+[m
[32m+[m[32m    # Track seats[m
[32m+[m[32m    seats_remaining = {selected_companies[i]: group_buckets[i] for i in range(num_companies)}[m
[32m+[m
[32m+[m[32m    # Helper to compute fragility[m
[32m+[m[32m    def compute_fragility(df):[m
[32m+[m[32m        frag = {}[m
[32m+[m[32m        for idx, row in df.iterrows():[m
[32m+[m[32m            count = 0[m
[32m+[m[32m            for c in selected_companies:[m
[32m+[m[32m                if c in df.columns:[m
[32m+[m[32m                    if row[c] <= 6:[m
[32m+[m[32m                        count += 1[m
[32m+[m[32m            frag[row['Student']] = count[m
[32m+[m[32m        return frag[m
[32m+[m
[32m+[m[32m    # --- Placement loop ---[m
[32m+[m[32m    while len(mdf) > 0:[m
[32m+[m
[32m+[m[32m        fragility = compute_fragility(mdf)[m
[32m+[m
[32m+[m[32m        # Select most fragile student[m
[32m+[m[32m        min_frag = min(fragility.values())[m
[32m+[m[32m        fragile_students = [s for s in fragility if fragility[s] == min_frag][m
[32m+[m[32m        current_student = fragile_students[0]  # arbitrary among equals[m
[32m+[m
[32m+[m[32m        student_row = mdf[mdf['Student'] == current_student].iloc[0][m
[32m+[m
[32m+[m[32m        best_option = None[m
[32m+[m[32m        best_tuple = (float('inf'), float('inf'), float('inf'))[m
[32m+[m
[32m+[m[32m        for company in selected_companies:[m
[32m+[m[32m            if seats_remaining[company] <= 0:[m
[32m+[m[32m                continue[m
[32m+[m
[32m+[m[32m            rank_value = student_row.get(company, 6)[m
[32m+[m
[32m+[m[32m            # Simulate removal[m
[32m+[m[32m            df_copy = mdf.drop(mdf[mdf['Student'] == current_student].index)[m
[32m+[m[32m            frag_after = compute_fragility(df_copy)[m
[32m+[m
[32m+[m[32m            backup_frag = 0[m
[32m+[m[32m            total_shift = 0[m
[32m+[m
[32m+[m[32m            for s in frag_after:[m
[32m+[m[32m                before = fragility.get(s, 0)[m
[32m+[m[32m                after = frag_after.get(s, 0)[m
[32m+[m[32m                if before >= 2 and after == 1:[m
[32m+[m[32m                    backup_frag += 1[m
[32m+[m[32m                total_shift += (before - after)[m
[32m+[m
[32m+[m[32m            candidate_tuple = (backup_frag, total_shift, rank_value)[m
[32m+[m
[32m+[m[32m            if candidate_tuple < best_tuple:[m
[32m+[m[32m                best_tuple = candidate_tuple[m
[32m+[m[32m                best_option = company[m
[32m+[m
[32m+[m[32m        # Fallback if no option[m
[32m+[m[32m        if best_option is None:[m
[32m+[m[32m            best_option = selected_companies[0][m
[32m+[m
[32m+[m[32m        # Assign[m
[32m+[m[32m        seat_index = group_buckets[selected_companies.index(best_option)] - seats_remaining[best_option][m
[32m+[m[32m        if best_option not in student_groups_df['Company'].values:[m
[32m+[m[32m            row_data = [best_option] + [None]*(2*max_group_size)[m
[32m+[m[32m            student_groups_df.loc[len(student_groups_df)] = row_data[m
[32m+[m
[32m+[m[32m        row_idx = student_groups_df[student_groups_df['Company'] == best_option].index[0][m
[32m+[m[32m        col_student = 1 + 2*seat_index[m
[32m+[m[32m        col_rank = col_student + 1[m
[32m+[m
[32m+[m[32m        student_groups_df.iloc[row_idx, col_student] = current_student[m
[32m+[m[32m        student_groups_df.iloc[row_idx, col_rank] = student_row.get(best_option, 6)[m
[32m+[m
[32m+[m[32m        seats_remaining[best_option] -= 1[m
[32m+[m[32m        mdf = mdf.drop(mdf[mdf['Student'] == current_student].index).reset_index(drop=True)[m
[32m+[m
[32m+[m[32m    return student_groups_df[m
 [m
 if __name__ == '__main__':[m
     main()[m
\ No newline at end of file[m
