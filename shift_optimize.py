import pyomo.environ as pyo
import csv
import configparser


def process_parameter_row_in_csv(data, row, name):

    """
    パラメータに関する行の処理
    days: 日数
    n_people: 人数
    alpha: 人によってシフト時間の合計が偏らないようにするための目的関数に関する重み
    beta: 人によって屋外のシフト時間の合計が偏らないようにするための目的関数に関する重み
    gamma: 人によって屋内のシフト時間の合計が偏らないようにするための目的関数に関する重み
    delta: 屋内企画に欲しい人数に近づけるための目的関数に関する重み
    epsilon: 屋外企画に欲しい人数に近づけるための目的関数に関する重み
    zeta: 屋内企画と屋外企画の行き来を少なくするための目的関数に関する重み
    eta: 短すぎるシフトを避けるための目的関数に関する重み
    """

    if len(row) != 2:
        raise ValueError(f"The format of the line describing {name} is incorrect.")
    if row[0] != name:
        raise ValueError(f"The place where it should be written as {name} is written as {row[0]}.")
    data[name] = int(row[1])


def process_time_row_in_csv(data, row):

    """
    開始時刻終了時刻に関する行の処理
    day{d}_start_time: d日目(0-indexed)の開始時刻
    day{d}_end_time: d日目の終了時刻
    開始/終了時刻がある時間表現(時間区間)は、[開始時刻, 終了時刻)を意味している
    (つまり、終了時刻自体は含まない)
    また、11時は22、13時半は27など、時刻は時を2倍した整数値として考えている
    """

    if len(row) != data['days'] * 3:
        raise ValueError(f"The format of the line describing start time and end time is incorrect.")
    for day_ind in range(data['days']):
        if row[day_ind * 3] != f'day{day_ind + 1}':
            raise ValueError(f"The place where it should be written as day{day_ind + 1} is written as {row[day_ind * 3]}.")
        data[f'day{day_ind}_start_time'] = int(row[day_ind * 3 + 1])
        data[f'day{day_ind}_end_time'] = int(row[day_ind * 3 + 2])


def process_n_people_row_in_csv(data, row, real_row_ind, day_ind):

    """
    企画に必要な人数に関する行の処理
    day{d}_{t}_needed_in: d日目の時刻tで屋内企画に必要な人数
    day{d}_{t}_needed_out: d日目の時刻tで屋外企画に必要な人数
    day{d}_{t}_wanted_in: d日目の時刻tで屋内企画に欲しい人数
    day{d}_{t}_wanted_out: d日目の時刻tで屋外企画に欲しい人数
    """

    if len(row) != 5:
        raise ValueError(f"The format of the line describing the number of people is incorrect.")
    if int(row[0]) != data[f'day{day_ind}_start_time'] + real_row_ind:
        raise ValueError(f"The place where it should be written as {data[f'day{day_ind}_start_time'] + real_row_ind} is written as {row[0]}.")
    data[f'day{day_ind}_{row[0]}_needed_in'] = int(row[1])
    data[f'day{day_ind}_{row[0]}_needed_out'] = int(row[2])
    data[f'day{day_ind}_{row[0]}_wanted_in'] = int(row[3])
    data[f'day{day_ind}_{row[0]}_wanted_out'] = int(row[4])


def process_person_row_in_csv(data, row, person_ind):

    """
    人に関する列の処理
    person{p}_name: 人pの名前
    person{p}_name2: 人pの名前2
    person{p}_days: 人pが参加可能な日のリスト
    person{p}_day{d}_n_ints: 人pがd日目に参加可能な時間区間の数
    person{p}_day{d}_avail_all: 人pがd日目に参加可能な時間(屋内屋外の合計)
    person{p}_day{d}_avail_out: 人pがd日目に参加可能な時間(屋外のみ)
    person{p}_day{d}_int{i}_start_time: 人pがd日目に参加可能なi個目(0-indexed)の時間区間の開始時刻
    person{p}_day{d}_int{i}_end_time: 人pがd日目に参加可能なi個目の時間区間の終了時刻
    """

    if len(row) == 0:
        raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
    data[f'person{person_ind}_name'] = row[0]
    data[f'person{person_ind}_name2'] = row[1]
    data[f'person{person_ind}_days'] = []
    day_ind = -1
    cond = 4
    for col_ind in range(2, len(row)):
        if row[col_ind][0:3] == "day" and cond == 4:
            if int(row[col_ind][3]) - 1 < 0 or int(row[col_ind][3]) - 1 >= data['days']:
                raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
            day_ind = int(row[col_ind][3]) - 1
            data[f'person{person_ind}_days'].append(int(row[col_ind][3]) - 1)
            data[f'person{person_ind}_day{day_ind}_n_ints'] = 0
            cond = 0
        elif cond == 0:
            if int(row[col_ind]) <= 0 and int(row[col_ind]) != -1:
                raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
            data[f'person{person_ind}_day{day_ind}_avail_all'] = int(row[col_ind])
            cond = 1
        elif cond == 1:
            if int(row[col_ind]) < 0 and int(row[col_ind]) != -1:
                raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
            data[f'person{person_ind}_day{day_ind}_avail_out'] = int(row[col_ind])
            cond = 2
        elif cond == 2 or cond == 4:
            if int(row[col_ind]) < data[f'day{day_ind}_start_time'] or int(row[col_ind]) > data[f'day{day_ind}_end_time']:
                raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
            data[f'person{person_ind}_day{day_ind}_n_ints'] += 1
            n_int = data[f'person{person_ind}_day{day_ind}_n_ints']
            data[f'person{person_ind}_day{day_ind}_int{n_int - 1}_start_time'] = int(row[col_ind])
            cond = 3
        elif cond == 3:
            if int(row[col_ind]) < data[f'day{day_ind}_start_time'] or int(row[col_ind]) > data[f'day{day_ind}_end_time']:
                raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
            n_int = data[f'person{person_ind}_day{day_ind}_n_ints']
            if data[f'person{person_ind}_day{day_ind}_int{n_int - 1}_start_time'] > int(row[col_ind]):
                raise ValueError(f"The format of the line describing person {person_ind} is incorrect.")
            data[f'person{person_ind}_day{day_ind}_int{n_int - 1}_end_time']= int(row[col_ind])
            cond = 4
        else:
            ValueError(f"The format of the line describing person {person_ind} is incorrect.")


def process_condition_row_in_csv(data, row, cond_ind):

    """
    制約に関する行の処理
    condition{c}_type: c番目の制約の種類
    condition{c}_constant: c番目の制約の定数項
    condition{c}_coefficient{t}: c番目の制約のt個目の項の係数
    condition{c}_variable{t}: c番目の制約のt個目の項の変数
    condition{c}_n_terms: c番目の制約の項数
    """

    if len(row) <= 3:
        raise ValueError(f"The format of the line describing condition {cond_ind + 1} is incorrect.")
    data[f'condition{cond_ind + 1}_type'] = int(row[0])
    data[f'condition{cond_ind + 1}_constant'] = int(row[1])
    col_ind = 2
    while col_ind < len(row):
        data[f'condition{cond_ind + 1}_coefficient{col_ind // 2}'] = int(row[col_ind])
        col_ind += 1
        data[f'condition{cond_ind + 1}_variable{col_ind // 2}'] = row[col_ind]
        col_ind += 1
    data[f'condition{cond_ind + 1}_n_terms'] = col_ind // 2 - 1


def read_csv(data_path):

    """csvデータで表されたシフト希望のデータを取得"""

    data = {}
    sum_time = []
    specify_row_index = [10]
    data['n_conditions'] = 0
    with open(data_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row_ind, row in enumerate(reader):
            while row and row[-1] == "":
                row.pop()
            if row_ind <= 8:
                if (row_ind == 0): process_parameter_row_in_csv(data, row, 'days')
                if (row_ind == 1): process_parameter_row_in_csv(data, row, 'n_people')
                if (row_ind == 2): process_parameter_row_in_csv(data, row, 'alpha')
                if (row_ind == 3): process_parameter_row_in_csv(data, row, 'beta')
                if (row_ind == 4): process_parameter_row_in_csv(data, row, 'gamma')
                if (row_ind == 5): process_parameter_row_in_csv(data, row, 'delta')
                if (row_ind == 6): process_parameter_row_in_csv(data, row, 'epsilon')
                if (row_ind == 7): process_parameter_row_in_csv(data, row, 'zeta')
                if (row_ind == 8): process_parameter_row_in_csv(data, row, 'eta')
            elif row_ind == 9:
                process_time_row_in_csv(data, row)
                for day_index in range(data['days']):
                    sum_time.append(data[f'day{day_index}_end_time'] - data[f'day{day_index}_start_time'])
                    specify_row_index.append(specify_row_index[day_index] + sum_time[day_index])
            elif row_ind >= 10 and row_ind < 10 + sum(sum_time):
                for day_index in range(data['days']):
                    if row_ind >= specify_row_index[day_index] and row_ind < specify_row_index[day_index + 1]:
                        process_n_people_row_in_csv(data, row, row_ind - specify_row_index[day_index], day_index)
            elif row_ind >= 10 + sum(sum_time) and row_ind < 10 + sum(sum_time) + data['n_people']:
                process_person_row_in_csv(data, row, row_ind - (10 + sum(sum_time)))
            elif row_ind >= 10 + sum(sum_time) + data['n_people']:
                process_condition_row_in_csv(data, row, row_ind - (10 + sum(sum_time) + data['n_people']))
                data['n_conditions'] += 1
    return data


def define_index(model, data):

    """
    添字を定義
    model.d: (日d)のリスト
    model.pd: (人p, 日d)のペアのリスト
    model.dt: (日d, 時t)のペアのリスト
    model.pdt: (人p, 日d, 時t)のタプルのリスト
    model.pdi: (人p, 日d, 区間i)のタプルのリスト
    """

    days = []
    for day_ind in range(data['days']):
        days.append(day_ind)
    model.d = pyo.Set(initialize=days)
    people_days = []
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            people_days.append((person_ind, day_ind))
    model.pd = pyo.Set(initialize=people_days)
    days_times = []
    for day_ind in range(data['days']):
        for time in range(data[f'day{day_ind}_start_time'], data[f'day{day_ind}_end_time']):
            days_times.append((day_ind, time))
    model.dt = pyo.Set(initialize=days_times)
    people_days_times = []
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            for int_ind in range(data[f'person{person_ind}_day{day_ind}_n_ints']):
                pdi_start = data[f'person{person_ind}_day{day_ind}_int{int_ind}_start_time']
                pdi_end = data[f'person{person_ind}_day{day_ind}_int{int_ind}_end_time']
                for time in range(pdi_start, pdi_end):
                    people_days_times.append((person_ind, day_ind, time))
    model.pdt = pyo.Set(initialize=people_days_times)
    people_days_ints = []
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            for int_ind in range(data[f'person{person_ind}_day{day_ind}_n_ints']):
                people_days_ints.append((person_ind, day_ind, int_ind))
    model.pdi = pyo.Set(initialize=people_days_ints)


def define_parameters(model, data):

    """
    パラメータを定義
    model.alpha-model.eta: 目的関数のパラメータ
    model.bigM: big-M、変数の上界を考えるときなどに使うバラメータ
    model.dt_needed_in: d日目の時刻tで屋内企画に必要な人数
    model.dt_needed_out: d日目の時刻tで屋外企画に必要な人数
    model.dt_person: d日目の時刻tで参加可能な人のリスト
    pd_avail_all: 人pがd日目に参加可能な時間(屋内屋外の合計)
    pd_avail_out: 人pがd日目に参加可能な時間(屋外のみ)
    pd_time = 人pがd日目に参加可能な時刻のリスト
    pd_n_ints = 人pがd日目に参加可能な時間区間の数
    pd_ints = 人pがd日目に参加可能な時間区間のリスト
    pdi_start = 人pがd日目に参加可能なi個目の時間区間の開始時刻
    pdi_end = 人pがd日目に参加可能なi個目の時間区間の終了時刻
    person{p}_day{d}_int{i}_start_time: 人pがd日目に参加可能なi個目(0-indexed)の時間区間の開始時刻
    person{p}_day{d}_int{i}_end_time: 人pがd日目に参加可能なi個目の時間区間の終了時刻
    d_start: d日目の開始時刻
    d_start: d日目の終了時刻
    """

    model.alpha = pyo.Param(initialize=data['alpha'])
    model.beta = pyo.Param(initialize=data['beta'])
    model.gamma = pyo.Param(initialize=data['gamma'])
    model.delta = pyo.Param(initialize=data['delta'])
    model.epsilon = pyo.Param(initialize=data['epsilon'])
    model.zeta = pyo.Param(initialize=data['zeta'])
    model.eta = pyo.Param(initialize=data['eta'])
    model.data = data

    bigM = 0
    for day_ind in range(data['days']):
        bigM = max(bigM, data[f'day{day_ind}_end_time'] - data[f'day{day_ind}_start_time'])
    model.bigM = pyo.Param(initialize=bigM+2)

    dt_needed_in = {}
    dt_needed_out = {}
    dt_person = {}
    for day_ind in range(data['days']):
        for time in range(data[f'day{day_ind}_start_time'], data[f'day{day_ind}_end_time']):
            dt_needed_in[(day_ind, time)] = data[f'day{day_ind}_{time}_needed_in']
            dt_needed_out[(day_ind, time)] = data[f'day{day_ind}_{time}_needed_out']
            dt_person[(day_ind, time)] = []
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            for int_ind in range(data[f'person{person_ind}_day{day_ind}_n_ints']):
                pdi_start = data[f'person{person_ind}_day{day_ind}_int{int_ind}_start_time']
                pdi_end = data[f'person{person_ind}_day{day_ind}_int{int_ind}_end_time']
                for time in range(pdi_start, pdi_end):
                    dt_person[(day_ind, time)].append(person_ind)
    model.dt_needed_in = pyo.Param(model.dt, initialize=dt_needed_in)
    model.dt_needed_out = pyo.Param(model.dt, initialize=dt_needed_out)
    model.dt_person = pyo.Param(model.dt, initialize=dt_person, within=pyo.Any)

    pd_avail_all = {}
    pd_avail_out = {}
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            if data[f'person{person_ind}_day{day_ind}_avail_all'] != -1:
                pd_avail_all[(person_ind, day_ind)] = data[f'person{person_ind}_day{day_ind}_avail_all']
            else:
                pd_avail_all[(person_ind, day_ind)] = model.bigM
            if data[f'person{person_ind}_day{day_ind}_avail_out'] != -1:
                pd_avail_out[(person_ind, day_ind)] = data[f'person{person_ind}_day{day_ind}_avail_out']
            else:
                pd_avail_out[(person_ind, day_ind)] = model.bigM
    model.pd_avail_all = pyo.Param(model.pd, initialize=pd_avail_all)
    model.pd_avail_out = pyo.Param(model.pd, initialize=pd_avail_out)

    pd_time = {}
    pd_n_ints = {}
    pd_ints = {}
    pdi_start = {}
    pdi_end = {}
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            pd_time[(person_ind, day_ind)] = []
            pd_n_ints[(person_ind, day_ind)] = data[f'person{person_ind}_day{day_ind}_n_ints']
            pd_ints[(person_ind, day_ind)] = []
    for person_ind in range(data['n_people']):
        for day_ind in data[f'person{person_ind}_days']:
            for int_ind in range(data[f'person{person_ind}_day{day_ind}_n_ints']):
                pdi_start_ = data[f'person{person_ind}_day{day_ind}_int{int_ind}_start_time']
                pdi_end_ = data[f'person{person_ind}_day{day_ind}_int{int_ind}_end_time']
                for time in range(pdi_start_, pdi_end_):
                    pd_time[(person_ind, day_ind)].append(time)
                pdi_start[(person_ind, day_ind, int_ind)] = data[f'person{person_ind}_day{day_ind}_int{int_ind}_start_time']
                pdi_end[(person_ind, day_ind, int_ind)] = data[f'person{person_ind}_day{day_ind}_int{int_ind}_end_time']
                pd_ints[(person_ind, day_ind)].append(int_ind)
    model.pd_time = pyo.Param(model.pd, initialize=pd_time, within=pyo.Any)
    model.pd_n_ints = pyo.Param(model.pd, initialize=pd_n_ints)
    model.pdi_start = pyo.Param(model.pdi, initialize=pdi_start)
    model.pdi_end = pyo.Param(model.pdi, initialize=pdi_end)
    model.pd_ints = pyo.Param(model.pd, initialize=pd_ints, within=pyo.Any)

    d_start = {}
    d_end = {}
    for day_ind in range(data['days']):
        d_start[day_ind] = data[f'day{day_ind}_start_time']
        d_end[day_ind] = data[f'day{day_ind}_end_time']
    model.d_start = pyo.Param(model.d, initialize=d_start)
    model.d_end = pyo.Param(model.d, initialize=d_end)


def bounds_start_end(model, person_ind, day_ind):

    """開始/終了時刻に関する制約"""

    return (model.d_start[day_ind], model.d_end[day_ind])


def define_variable(model):

    """
    変数を定義
    model.us: 人pの日dにおけるシフト開始時刻(全体)
    model.ue: 人pの日dにおけるシフト終了時刻(全体)
    model.vs: 人pの日dにおけるシフト開始時刻(屋外)
    model.ve: 人pの日dにおけるシフト終了時刻(屋外)
    model.x: 人pの日dにおいて時刻tにシフトが入っているか(全体)
    model.y: 人pの日dにおいて時刻tにシフトが入っているか(屋外)
    model.i: 人pの比dにおけるi個目の希望時間区間を使うか
    model.z1: インジケータ変数1
    model.z2: インジケータ変数2
    model.z3: インジケータ変数3
    model.z4: インジケータ変数4
    model.ss: 人pの日dにおけるシフト開始時刻(全体)とシフト開始時刻(屋外)が一致しているか
    model.se: 人pの日dにおけるシフト終了時刻(全体)とシフト終了時刻(屋外)が一致しているか
    model.ts: 人pの日dにおけるシフトが短すぎるか
    model.z5: インジケータ変数5
    model.z6: インジケータ変数6
    """

    model.us = pyo.Var(model.pd, domain=pyo.Integers, bounds=bounds_start_end)
    model.ue = pyo.Var(model.pd, domain=pyo.Integers, bounds=bounds_start_end)
    model.vs = pyo.Var(model.pd, domain=pyo.Integers, bounds=bounds_start_end)
    model.ve = pyo.Var(model.pd, domain=pyo.Integers, bounds=bounds_start_end)
    model.x = pyo.Var(model.pdt, domain=pyo.Binary)
    model.y = pyo.Var(model.pdt, domain=pyo.Binary)
    model.i = pyo.Var(model.pdi, domain=pyo.Binary)
    model.z1 = pyo.Var(model.pdt, domain=pyo.Binary)
    model.z2 = pyo.Var(model.pdt, domain=pyo.Binary)
    model.z3 = pyo.Var(model.pdt, domain=pyo.Binary)
    model.z4 = pyo.Var(model.pdt, domain=pyo.Binary)
    model.ss = pyo.Var(model.pd, domain=pyo.Binary)
    model.se = pyo.Var(model.pd, domain=pyo.Binary)
    model.ts = pyo.Var(model.pd, domain=pyo.Binary)
    model.z5 = pyo.Var(model.pd, domain=pyo.Binary)
    model.z6 = pyo.Var(model.pd, domain=pyo.Binary)


def rule_needed_in(model, day_ind, time):
    return (sum(model.x[(person_ind, day_ind, time)] for person_ind in model.dt_person[day_ind, time]) -
        sum(model.y[(person_ind, day_ind, time)] for person_ind in model.dt_person[day_ind, time]) >= model.dt_needed_in[(day_ind, time)])

def rule_needed_out(model, day_ind, time):
    return sum(model.y[(person_ind, day_ind, time)] for person_ind in model.dt_person[day_ind, time]) >= model.dt_needed_out[(day_ind, time)]

def rule_avail_all(model, person_ind, day_ind):
    return sum(model.x[(person_ind, day_ind, time)] for time in model.pd_time[person_ind, day_ind]) <= model.pd_avail_all[(person_ind, day_ind)]

def rule_avail_out(model, person_ind, day_ind):
    return sum(model.y[(person_ind, day_ind, time)] for time in model.pd_time[person_ind, day_ind]) <= model.pd_avail_out[(person_ind, day_ind)]

def rule_order1(model, person_ind, day_ind):
    return model.vs[(person_ind, day_ind)] <= model.ve[(person_ind, day_ind)]

def rule_order2(model, person_ind, day_ind):
    return model.us[(person_ind, day_ind)] <= model.vs[(person_ind, day_ind)]

def rule_order3(model, person_ind, day_ind):
    return model.ve[(person_ind, day_ind)] <= model.ue[(person_ind, day_ind)]

def rule_binary_int_all1(model, person_ind, day_ind, time):
    return time - model.us[(person_ind, day_ind)] >= - model.bigM * (1 - model.z1[(person_ind, day_ind, time)])

def rule_binary_int_all2(model, person_ind, day_ind, time):
    return time - model.us[(person_ind, day_ind)] <= model.bigM * model.z1[(person_ind, day_ind, time)] - 1

def rule_binary_int_all3(model, person_ind, day_ind, time):
    return model.ue[(person_ind, day_ind)] - time >= - model.bigM * (1 - model.z2[(person_ind, day_ind, time)]) + 1

def rule_binary_int_all4(model, person_ind, day_ind, time):
    return model.ue[(person_ind, day_ind)] - time <= model.bigM * model.z2[(person_ind, day_ind, time)]

def rule_binary_int_all5(model, person_ind, day_ind, time):
    return model.x[(person_ind, day_ind, time)] <= model.z1[(person_ind, day_ind, time)]

def rule_binary_int_all6(model, person_ind, day_ind, time):
    return model.x[(person_ind, day_ind, time)] <= model.z2[(person_ind, day_ind, time)]

def rule_binary_int_all7(model, person_ind, day_ind, time):
    return model.x[(person_ind, day_ind, time)] >= model.z1[(person_ind, day_ind, time)] + model.z2[(person_ind, day_ind, time)] - 1

def rule_binary_int_in1(model, person_ind, day_ind, time):
    return time - model.vs[(person_ind, day_ind)] >= - model.bigM * (1 - model.z3[(person_ind, day_ind, time)])

def rule_binary_int_in2(model, person_ind, day_ind, time):
    return time - model.vs[(person_ind, day_ind)] <= model.bigM * model.z3[(person_ind, day_ind, time)] - 1

def rule_binary_int_in3(model, person_ind, day_ind, time):
    return model.ve[(person_ind, day_ind)] - time >= - model.bigM * (1 - model.z4[(person_ind, day_ind, time)]) + 1

def rule_binary_int_in4(model, person_ind, day_ind, time):
    return model.ue[(person_ind, day_ind)] - time <= model.bigM * model.z4[(person_ind, day_ind, time)]

def rule_binary_int_in5(model, person_ind, day_ind, time):
    return model.y[(person_ind, day_ind, time)] <= model.z3[(person_ind, day_ind, time)]

def rule_binary_int_in6(model, person_ind, day_ind, time):
    return model.y[(person_ind, day_ind, time)] <= model.z4[(person_ind, day_ind, time)]

def rule_binary_int_in7(model, person_ind, day_ind, time):
    return model.y[(person_ind, day_ind, time)] >= model.z3[(person_ind, day_ind, time)] + model.z4[(person_ind, day_ind, time)] - 1

def rule_shift_in_interval1(model, person_ind, day_ind, int_ind):
    return (model.us[(person_ind, day_ind)] - model.pdi_start[(person_ind, day_ind, int_ind)] >=
        - model.bigM * (1 - model.i[(person_ind, day_ind, int_ind)]))

def rule_shift_in_interval2(model, person_ind, day_ind, int_ind):
    return (model.pdi_end[(person_ind, day_ind, int_ind)] - model.ue[(person_ind, day_ind)] >=
        - model.bigM * (1 - model.i[(person_ind, day_ind, int_ind)]))

def rule_shift_in_interval3(model, person_ind, day_ind):
    return sum(model.i[(person_ind, day_ind, int_ind)] for int_ind in model.pd_ints[person_ind, day_ind]) >= 1

def rule_same_start_in_all1(model, person_ind, day_ind):
    return model.us[(person_ind, day_ind)] - model.vs[(person_ind, day_ind)] >= - model.bigM * (1 - model.ss[(person_ind, day_ind)])

def rule_same_start_in_all2(model, person_ind, day_ind):
    return model.vs[(person_ind, day_ind)] - model.us[(person_ind, day_ind)] >= - model.bigM * (1 - model.ss[(person_ind, day_ind)])

def rule_same_end_in_all1(model, person_ind, day_ind):
    return model.ue[(person_ind, day_ind)] - model.ve[(person_ind, day_ind)] >= - model.bigM * (1 - model.se[(person_ind, day_ind)])

def rule_same_end_in_all2(model, person_ind, day_ind):
    return model.ve[(person_ind, day_ind)] - model.ue[(person_ind, day_ind)] >= - model.bigM * (1 - model.se[(person_ind, day_ind)])

def rule_too_short1(model, person_ind, day_ind):
    return model.ue[(person_ind, day_ind)] - model.us[(person_ind, day_ind)] >= - model.bigM * model.z5[(person_ind, day_ind)] + 3

def rule_too_short2(model, person_ind, day_ind):
    return model.ue[(person_ind, day_ind)] - model.us[(person_ind, day_ind)] <= model.bigM * model.z6[(person_ind, day_ind)]

def rule_too_short3(model, person_ind, day_ind):
    return model.ts[(person_ind, day_ind)] >= model.z5[(person_ind, day_ind)] + model.z6[(person_ind, day_ind)] - 1
    

def define_constraints(model):

    """
    制約を定義
    rule_needed_in: それぞれの時刻に必要な屋内企画の人数に関する制約"
    rule_needed_out: それぞれの時刻に必要な屋外企画の人数に関する制約
    rule_avail_all: それぞれの人がそれぞれの日で働ける最大時間に関する制約(全体)
    rule_avail_out: それぞれの人がそれぞれの日で働ける最大時間に関する制約(屋外)
    rule_order1: 屋内のシフト開始時刻<=屋内のシフト終了時刻という制約
    rule_order2: 全体のシフト開始時刻<=屋内のシフト開始時刻という制約
    rule_order3: 屋内のシフト終了時刻<=全体のシフト終了時刻という制約
    rule_binary_int_all1: 01変数と整数変数をつなぐ制約1(全体)
    rule_binary_int_all2: 01変数と整数変数をつなぐ制約2(全体)
    rule_binary_int_all3: 01変数と整数変数をつなぐ制約3(全体)
    rule_binary_int_all4: 01変数と整数変数をつなぐ制約4(全体)
    rule_binary_int_all5: 01変数と整数変数をつなぐ制約5(全体)
    rule_binary_int_all6: 01変数と整数変数をつなぐ制約6(全体)
    rule_binary_int_all7: 01変数と整数変数をつなぐ制約7(全体)
    rule_binary_int_in1: 01変数と整数変数をつなぐ制約1(屋内)
    rule_binary_int_in2: 01変数と整数変数をつなぐ制約2(屋内)
    rule_binary_int_in3: 01変数と整数変数をつなぐ制約3(屋内)
    rule_binary_int_in4: 01変数と整数変数をつなぐ制約4(屋内)
    rule_binary_int_in5: 01変数と整数変数をつなぐ制約5(屋内)
    rule_binary_int_in6: 01変数と整数変数をつなぐ制約6(屋内)
    rule_binary_int_in7: 01変数と整数変数をつなぐ制約7(屋内)
    rule_shift_in_interval1: シフトが希望時間区間にあるという制約1
    rule_shift_in_interval2: シフトが希望時間区間にあるという制約2
    rule_shift_in_interval3: シフトが希望時間区間にあるという制約3
    rule_same_start_in_all1: 開始時刻が全体と屋内で同じかを表す制約1
    rule_same_start_in_all2: 開始時刻が全体と屋内で同じかを表す制約2
    rule_same_end_in_all1: 終了時刻が全体と屋内で同じかを表す制約1
    rule_same_end_in_all2: 終了時刻が全体と屋内で同じかを表す制約2
    rule_too_short1: ある日のシフトの時間が短すぎるかを表す制約1
    rule_too_short2: ある日のシフトの時間が短すぎるかを表す制約2
    rule_too_short3: ある日のシフトの時間が短すぎるかを表す制約3
    """

    model.c_needed_in = pyo.Constraint(model.dt, rule=rule_needed_in)
    model.c_needed_out = pyo.Constraint(model.dt, rule=rule_needed_out)
    model.c_avail_all = pyo.Constraint(model.pd, rule=rule_avail_all)
    model.c_avail_out = pyo.Constraint(model.pd, rule=rule_avail_out)
    model.c_order1 = pyo.Constraint(model.pd, rule=rule_order1)
    model.c_order2 = pyo.Constraint(model.pd, rule=rule_order2)
    model.c_order3 = pyo.Constraint(model.pd, rule=rule_order3)
    model.c_binary_int_all1 = pyo.Constraint(model.pdt, rule=rule_binary_int_all1)
    model.c_binary_int_all2 = pyo.Constraint(model.pdt, rule=rule_binary_int_all2)
    model.c_binary_int_all3 = pyo.Constraint(model.pdt, rule=rule_binary_int_all3)
    model.c_binary_int_all4 = pyo.Constraint(model.pdt, rule=rule_binary_int_all4)
    model.c_binary_int_all5 = pyo.Constraint(model.pdt, rule=rule_binary_int_all5)
    model.c_binary_int_all6 = pyo.Constraint(model.pdt, rule=rule_binary_int_all6)
    model.c_binary_int_all7 = pyo.Constraint(model.pdt, rule=rule_binary_int_all7)
    model.c_binary_int_in1 = pyo.Constraint(model.pdt, rule=rule_binary_int_in1)
    model.c_binary_int_in2 = pyo.Constraint(model.pdt, rule=rule_binary_int_in2)
    model.c_binary_int_in3 = pyo.Constraint(model.pdt, rule=rule_binary_int_in3)
    model.c_binary_int_in4 = pyo.Constraint(model.pdt, rule=rule_binary_int_in4)
    model.c_binary_int_in5 = pyo.Constraint(model.pdt, rule=rule_binary_int_in5)
    model.c_binary_int_in6 = pyo.Constraint(model.pdt, rule=rule_binary_int_in6)
    model.c_binary_int_in7 = pyo.Constraint(model.pdt, rule=rule_binary_int_in7)
    model.c_shift_in_interval1 = pyo.Constraint(model.pdi, rule=rule_shift_in_interval1)
    model.c_shift_in_interval2 = pyo.Constraint(model.pdi, rule=rule_shift_in_interval2)
    model.c_shift_in_interval3 = pyo.Constraint(model.pd, rule=rule_shift_in_interval3)
    model.c_same_start_in_all1 = pyo.Constraint(model.pd, rule=rule_same_start_in_all1)
    model.c_same_start_in_all2 = pyo.Constraint(model.pd, rule=rule_same_start_in_all2)
    model.c_same_end_in_all1 = pyo.Constraint(model.pd, rule=rule_same_end_in_all1)
    model.c_same_end_in_all2 = pyo.Constraint(model.pd, rule=rule_same_end_in_all2)
    model.c_rule_too_short1 = pyo.Constraint(model.pd, rule=rule_too_short1)
    model.c_rule_too_short2 = pyo.Constraint(model.pd, rule=rule_too_short2)
    model.c_rule_too_short3 = pyo.Constraint(model.pd, rule=rule_too_short3)


def get_model_variable(model, variable_str):

    """変数名を文字列からモデルの変数へと変換"""

    if variable_str.startswith("us["):
        inside = variable_str[3:-1]
        p, d = map(int, inside.split(","))
        return model.us[p, d]
    elif variable_str.startswith("ue["):
        inside = variable_str[3:-1]
        p, d = map(int, inside.split(","))
        return model.ue[p, d]
    elif variable_str.startswith("vs["):
        inside = variable_str[3:-1]
        p, d = map(int, inside.split(","))
        return model.vs[p, d]
    elif variable_str.startswith("ve["):
        inside = variable_str[3:-1]
        p, d = map(int, inside.split(","))
        return model.ve[p, d]
    elif variable_str.startswith("x["):
        inside = variable_str[2:-1]
        p, d, t = map(int, inside.split(","))
        return model.x[p, d, t]
    elif variable_str.startswith("y["):
        inside = variable_str[2:-1]
        p, d, t = map(int, inside.split(","))
        return model.y[p, d, t]
    else:
        raise ValueError(f"Unknown variable: {variable_str}")


def define_extra_constraints(model, data):

    """新たな制約を定義"""

    model.extra_constraints = pyo.ConstraintList()
    for cond_ind in range(data['n_conditions']):
        expr = sum(data[f'condition{cond_ind + 1}_coefficient{term_ind + 1}'] *
            get_model_variable(model, data[f'condition{cond_ind + 1}_variable{term_ind + 1}']) 
            for term_ind in range(data[f'condition{cond_ind + 1}_n_terms']))
        if data[f'condition{cond_ind + 1}_type'] == 0:
            model.extra_constraints.add(expr <= data[f'condition{cond_ind + 1}_constant'])
        elif data[f'condition{cond_ind + 1}_type'] == 1:
            model.extra_constraints.add(expr >= data[f'condition{cond_ind + 1}_constant'])
        else:
            model.extra_constraints.add(expr == data[f'condition{cond_ind + 1}_constant'])


def define_objective(model):

    """目的関数を定義"""

    return model.alpha * sum(
        (sum((model.ue[person_ind, day_ind] - model.us[person_ind, day_ind]) for day_ind in model.data[f'person{person_ind}_days']))**2
        for person_ind in range(model.data['n_people'])
    ) + model.beta * sum(
        (sum((model.ve[person_ind, day_ind] - model.vs[person_ind, day_ind]) for day_ind in model.data[f'person{person_ind}_days']))**2
        for person_ind in range(model.data['n_people'])
    ) + model.gamma * sum(
        (sum((model.ue[person_ind, day_ind] - model.us[person_ind, day_ind] - model.ve[person_ind, day_ind] + model.vs[person_ind, day_ind])
        for day_ind in model.data[f'person{person_ind}_days']))**2 for person_ind in range(model.data['n_people'])
    ) + model.delta * sum((sum(model.x[(person_ind, day_ind, time)] - model.y[(person_ind, day_ind, time)]
        for person_ind in model.dt_person[day_ind, time]) - model.data[f"day{day_ind}_{time}_wanted_in"])**2 for (day_ind, time) in model.dt
    ) + model.epsilon * sum((sum(model.y[(person_ind, day_ind, time)] for person_ind in model.dt_person[day_ind, time]) - 
        model.data[f"day{day_ind}_{time}_wanted_out"])**2 for (day_ind, time) in model.dt
    ) - model.zeta * sum(sum(model.ss[(person_ind, day_ind)] + model.se[(person_ind, day_ind)]
        for day_ind in model.data[f'person{person_ind}_days']) for person_ind in range(model.data['n_people'])
    ) + model.eta * sum(sum(model.ts[(person_ind, day_ind)] for day_ind in model.data[f'person{person_ind}_days'])
        for person_ind in range(model.data['n_people'])
    )


def int_trans_time(time_int):

    """整数値を時刻HH:MMに変換する処理"""
    
    time_int = int(time_int)
    if time_int % 2 == 0:
        return str(time_int // 2) + ":00"
    else:
        return str(time_int // 2) + ":30"


def output_csv(model, data, data_path):

    """計算した最良のシフトをcsvで出力"""

    with open(data_path, "w", encoding="utf-8-sig", newline="") as f:

        writer = csv.writer(f)

        # 各列の説明を出力
        explain_row = []
        explain_row.append("名前")
        explain_row.append("名前2")
        for day_ind in range(data['days']):
            explain_row.append(f"{day_ind + 1}日目")
            explain_row.append(f"{day_ind + 1}日目 (うち屋外)")
        writer.writerow(explain_row)

        # それぞれの人のシフトを出力
        for person_ind in range(data['n_people']):
            person_row = []
            person_row.append(data[f'person{person_ind}_name'])
            person_row.append(data[f'person{person_ind}_name2'])
            for day_ind in range(data['days']):
                if (person_ind, day_ind) in model.pd:
                    if model.us[(person_ind, day_ind)].value < model.ue[(person_ind, day_ind)].value:
                        person_row.append(int_trans_time(model.us[(person_ind, day_ind)].value) + 
                            "～" + int_trans_time(model.ue[(person_ind, day_ind)].value))
                    else:
                        person_row.append("なし")
                    if model.vs[(person_ind, day_ind)].value < model.ve[(person_ind, day_ind)].value:
                        person_row.append(int_trans_time(model.vs[(person_ind, day_ind)].value) +
                            "～" + int_trans_time(model.ve[(person_ind, day_ind)].value))
                    else:
                        person_row.append("なし")
                else:
                    person_row.append("なし")
                    person_row.append("なし")
            writer.writerow(person_row)


def main():

    """メイン関数"""

    # settings.iniから情報を取得
    config = configparser.ConfigParser()
    config.read("settings.ini")
    shaped_path = config["path"]["shaped"]
    best_path = config["path"]["best"]
    solver_time = config["solver"]["time"]

    # シフト希望のデータを取得
    data = read_csv(shaped_path)

    # モデルを定義
    model = pyo.ConcreteModel()
    define_index(model, data)
    define_parameters(model, data)
    define_variable(model)
    define_constraints(model)
    define_extra_constraints(model, data)
    model.obj = pyo.Objective(rule=define_objective, sense=pyo.minimize)

    # ソルバーで求解
    opt = pyo.SolverFactory('gurobi')
    opt.options['TimeLimit'] = solver_time
    opt.options['MIPGap'] = 0.1
    opt.solve(model, tee=True)

    # 計算したシフトをcsvで出力
    output_csv(model, data, best_path)


if __name__ == "__main__":
    main()