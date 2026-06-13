from google import genai
from pydantic import BaseModel
from typing import List
import json
import csv
import configparser


# 時間区間のクラス
class TimeInterval(BaseModel):
    time_start: str
    time_end: str

# ある人のある日のシフト希望を表すクラス
class PersonOneday(BaseModel):
    day: int
    time_intervals: List[TimeInterval]
    desire_all: int
    desire_out: int

# ある人のシフト希望を表すクラス
class Person(BaseModel):
    person_oneday: List[PersonOneday]

# 線形制約の項を表すクラス
class Term(BaseModel):
    coefficient: int
    variable: str

# ある線形制約を表すクラス
class Condition(BaseModel):
    type: int
    terms: List[Term]
    constant: int

# シフト希望全体を表すクラス
class OutputAll(BaseModel):
    output_person: List[Person]
    conditions: List[Condition]


def time_trans_int(time, up):

    """時刻HH:MMを整数値に変換する処理"""

    hour = int(time[0:2])
    minute = int(time[3:5])
    if up == True:
        if minute == 0:
            return int(2 * hour)
        elif minute <= 30:
            return int(2 * hour + 1)
        else:
            return int(2 * hour + 2)
    else:
        if minute < 30:
            return int(2 * hour)
        else:
            return int(2 * hour + 1)


def int_trans_time(time_int):

    """整数値を時刻HH:MMに変換する処理"""
    
    time_int = int(time_int)
    if time_int % 2 == 0:
        return str(time_int // 2) + ":00"
    else:
        return str(time_int // 2) + ":30"


def process_parameter_row_in_csv(data, row, name):

    """パラメータに関する行の処理"""

    if len(row) != 2:
        raise ValueError(f"The format of the line describing {name} is incorrect.")
    if row[0] != name:
        raise ValueError(f"The place where it should be written as {name} is written as {row[0]}.")
    data[name] = int(row[1])


def process_time_row_in_csv(data, row):

    """開始時刻終了時刻に関する行の処理"""

    if len(row) != data['days'] * 3:
        raise ValueError(f"The format of the line describing start time and end time is incorrect.")
    for day_ind in range(data['days']):
        if row[day_ind * 3] != f'day{day_ind + 1}':
            raise ValueError(f"The place where it should be written as day{day_ind + 1} is written as {row[day_ind * 3]}.")
        data[f'day{day_ind}_start_time'] = int(row[day_ind * 3 + 1])
        data[f'day{day_ind}_end_time'] = int(row[day_ind * 3 + 2])
    

def process_what_row_in_csv(data, row):

    """何の列かを表す行の処理"""

    data['n_index'] = len(row)
    for index, name in enumerate(row):
        if name[0:3] != "day" and name[0:4] != "name":
            raise ValueError(f"The format of the line describing what is the column is incorrect.")
        if name[0:3] == "day":
            if int(name[3]) - 1 < 0 or int(name[3]) - 1 >= data['days']:
                raise ValueError(f"The format of the line describing what is the column is incorrect.")
            data[f'column{index}'] = int(name[3]) - 1
        if name[0:4] == "name":
            if int(name[4]) - 1 < 0 or int(name[4]) - 1 >= 2:
                raise ValueError(f"The format of the line describing what is the column is incorrect.")
            data[f'column{index}'] = - int(name[4])
    

def process_person_row_in_csv(data, row, person_ind):

    """人に関する行の処理"""

    person_data = {}
    for day_ind in range(data['days']):
        person_data[f'person{person_ind}_day{day_ind + 1}'] = []
    for index, sentence in enumerate(row):
        if (index < data['n_index']):
            day_ind = data[f'column{index}']
            if (day_ind >= 0):
                person_data[f'person{person_ind}_day{day_ind + 1}'].append(sentence)
            elif (day_ind == -1):
                data[f'person{person_ind}_name'] = sentence
            else:
                data[f'person{person_ind}_name2'] = sentence
    person_data_sum = []
    for day_ind in range(data['days']):
        person_data_sum.append(f"day{day_ind + 1}{{{','.join(person_data[f'person{person_ind}_day{day_ind + 1}'])}}}")
    data[f'person{person_ind}']= ",".join(person_data_sum)


def read_csv(data_path):

    """csvデータで表されたフォームの回答データを取得"""

    data = {}
    with open(data_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row_ind, row in enumerate(reader):
            while row and row[-1] == "" and row_ind <= 3:
                row.pop()
            if row_ind <= 1:
                if (row_ind == 0): process_parameter_row_in_csv(data, row, 'days')
                if (row_ind == 1): process_parameter_row_in_csv(data, row, 'n_people')
            if row_ind == 2:
                process_time_row_in_csv(data, row)
            if row_ind == 3:
                process_what_row_in_csv(data, row)
            if row_ind >= 4:
                process_person_row_in_csv(data, row, row_ind - 4)
    return data


def output_csv(data_path, data, parsed):

    """csvで表された整形データとして出力"""

    with open(data_path, "w", encoding="utf-8-sig", newline="") as f:

        # パラメータに関する行を出力
        writer = csv.writer(f)
        writer.writerow(["days", data['days']])
        writer.writerow(["n_people", data['n_people']])
        writer.writerow(["alpha", 1])
        writer.writerow(["beta", 5])
        writer.writerow(["gamma", 1])
        writer.writerow(["delta", 50])
        writer.writerow(["epsilon", 100])
        writer.writerow(["zeta", 25])
        writer.writerow(["eta", 150])

        # 開始時刻終了時刻に関する行を出力
        time_row = []
        for day_ind in range(data['days']):
            time_row.append(f"day{day_ind + 1}")
            time_row.append(data[f'day{day_ind}_start_time'])
            time_row.append(data[f'day{day_ind}_end_time'])
        writer.writerow(time_row)

        # 企画に必要な人数に関する行を出力
        for day_ind in range(data['days']):
            for time in range(data[f'day{day_ind}_start_time'], data[f'day{day_ind}_end_time']):
                writer.writerow([time, 8, 3, 11, 3])

        # 人に関する行を出力
        for person_ind in range(data['n_people']):
            person_row = []
            person_row.append(data[f'person{person_ind}_name'])
            person_row.append(data[f'person{person_ind}_name2'])
            for person_oneday in parsed.output_person[person_ind].person_oneday:
                person_row.append(f"day{person_oneday.day}")
                person_row.append(person_oneday.desire_all)
                person_row.append(person_oneday.desire_out)
                for ints in person_oneday.time_intervals:
                    person_row.append(time_trans_int(ints.time_start, True))
                    person_row.append(time_trans_int(ints.time_end, False))
            writer.writerow(person_row)

        # 制約に関する行を出力
        for cond_ind in parsed.conditions:
            cond_row = []
            cond_row.append(cond_ind.type)
            cond_row.append(cond_ind.constant)
            for term in cond_ind.terms:
                cond_row.append(term.coefficient)
                cond_row.append(term.variable)
            writer.writerow(cond_row)


def main():

    """メイン関数"""

    # settings.iniから情報を取得
    config = configparser.ConfigParser()
    config.read("settings.ini")
    GEMINI_API_KEY = config["api"]["api_key"]
    MODEL_NAME = config["api"]["model_name"]
    query_path = config["path"]["query"]
    shaped_path = config["path"]["shaped"]

    # フォームの回答データを取得
    data = read_csv(query_path)

    # システム指示文を取得
    with open("assets/shift_system_instruction.txt", "r", encoding="utf-8") as f:
        system_instruction = f.read()

    # システム指示文の可変部分を設定
    system_instruction = system_instruction.replace("{days}", str(data['days']))
    system_instruction = system_instruction.replace("{n_people}", str(data['n_people']))
    day_list = ""
    day_list_jp = ""
    explain_start_end_time = ""
    for day_ind in range(data['days']):
        day_list += f"day{day_ind + 1}"
        day_list_jp += f"{day_ind + 1}日目"
        explain_start_end_time += f"""{day_ind + 1}日目の開始時刻は{int_trans_time(data[f'day{day_ind}_start_time'])}、終了時刻は{int_trans_time(data[f'day{day_ind}_end_time'])}です。\n"""
        if day_ind != data['days'] - 1:
            day_list += "、"
            day_list_jp += "、"
    system_instruction = system_instruction.replace("{days_list}", day_list)
    system_instruction = system_instruction.replace("{days_list_jp}", day_list_jp)
    system_instruction = system_instruction.replace("{explain_start_end_time}", explain_start_end_time)

    # プロンプトを取得
    with open("assets/shift_prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read()

    # プロンプトの可変部分を設定
    for person_ind in range(0, data['n_people']):
        prompt += data[f'person{person_ind}'] + "\n"

    # Geminiに送信
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Sending the prompt to Gemini...")
    response = client.models.generate_content(
        model=MODEL_NAME, contents=prompt,
        config={ "temperature": 0, "thinking_config": {"thinking_level": "low"},
            "system_instruction": system_instruction, "response_mime_type": "application/json", "response_schema": OutputAll,
        },
    )
    print("Finished the process in Gemini")

    # 利用トークン数を表示
    usage = response.usage_metadata
    print("Prompt tokens:", usage.prompt_token_count)
    print("Output tokens:", usage.candidates_token_count)
    print("Total tokens:", usage.total_token_count)

    # 整形データとして出力
    output_csv(shaped_path, data, response.parsed)


if __name__ == "__main__":
    main()