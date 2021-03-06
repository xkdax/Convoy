if __name__ == '__main__':
    import pandas as pd
    import sqlite3
    import json
    from dicttoxml import dicttoxml


    def xlsx_to_csv(file):
        my_df = pd.read_excel(f'{file}', sheet_name='Vehicles', dtype=str)
        my_df.to_csv(f'{file.replace(".xlsx", ".csv")}', index=None, header=True)
        my_df = pd.read_csv(f'{file.replace(".xlsx", ".csv")}')
        _counter = len(my_df.index)
        if _counter != 1:
            print(f'{_counter} lines were imported to {file.replace(".xlsx", ".csv")}')
        else:
            print(f'{_counter} line was imported to {file.replace(".xlsx", ".csv")}')
        return file.replace(".xlsx", ".csv")


    def check_csv(file):
        with open(file, 'r') as opened_file:
            lines = opened_file.readlines()
            _counter = 0
            new_lines = [lines[0]]
            for line in lines[1:]:
                line = line.split(',')
                new_line = []
                for cell in line:
                    new_cell = ''
                    for sym in cell:
                        if sym.isdigit() or sym == '\n':
                            new_cell += sym
                    if cell != new_cell:
                        _counter += 1
                    new_line.append(new_cell)  # [cell_counter]
                new_lines.append(new_line)
        with open(file.replace('.csv', '[CHECKED].csv'), 'w') as opened_file:
            print(new_lines[0], file=opened_file, end='')
            for cell in new_lines[1:]:
                print(','.join(cell), file=opened_file, end='')
        if _counter != 1:
            print(f'{_counter} cells were corrected in {file.replace(".csv", "[CHECKED].csv")}')
        else:
            print(f'{_counter} cell was corrected in {file.replace(".csv", "[CHECKED].csv")}')
        return file.replace(".csv", "[CHECKED].csv")


    def csv_to_s3db(file):
        # открываем файл + пиздим всё
        with open(file, 'r') as opened_file:
            my_df = pd.read_csv(opened_file)
            _counter = my_df.shape[0]

            # ████████████████████████████████████████
            # █───██────██────██────██───██─██─██────█
            # █─████─██─██─██─██─██─███─███──█─██─████
            # █───██─█████─██─██────███─███─█──██─█──█
            # ███─██─██─██─██─██─█─████─███─██─██─██─█
            # █───██────██────██─█─███───██─██─██────█
            # ████████████████████████████████████████
            score = []
            for _i in range(_counter):
                score.append(0)
                if my_df['fuel_consumption'][_i] * 4.5 < my_df['engine_capacity'][_i]:
                    score[_i] += 2
                elif my_df['fuel_consumption'][_i] * 4.5 < my_df['engine_capacity'][_i] * 2:
                    score[_i] += 1
                if my_df['fuel_consumption'][_i] * 4.5 < 230:
                    score[_i] += 2
                else:
                    score[_i] += 1
                if my_df['maximum_load'][_i] >= 20:
                    score[_i] += 2
            my_df['score'] = score
            # ----------------------------------------
            # создаём + открываем с3дб файл
            conn = sqlite3.connect(file.replace('[CHECKED].csv', '.s3db'))
            if conn is not None:
                cur = conn.cursor()
                # грамотно закидываем всё туда
                cur.execute(f'create table if not exists convoy (vehicle_id int primary key,'
                            'engine_capacity int not null,'
                            'fuel_consumption int not null,'
                            'maximum_load int not null,'
                            'score int not null'
                            ');')
                my_df.to_sql(name='convoy', con=conn, if_exists='append', index=False)
                # закрываем
                conn.commit()
                cur.close()
                conn.close()
                # пишем результат и return
                if _counter != 1:
                    print(f'{_counter} records were inserted into {file.replace("[CHECKED].csv", ".s3db")}')
                else:
                    print(f'{_counter} record was inserted into {file.replace("[CHECKED].csv", ".s3db")}')
                return file.replace('[CHECKED].csv', '.s3db')
            else:
                print('sqlite3 connection suck')


    def s3db_to_json_and_xml(file):
        # залазаем в скл и всё пиздим
        # try:
        conn = sqlite3.connect(file)
        cur = conn.cursor()
        nvm = pd.read_sql_query("""select * from convoy""", con=conn)
        df_for_xml = nvm.to_dict(orient='records')
        my_df = {"convoy": eval(pd.read_sql_query('select * from convoy', con=conn).to_json(orient='records'))}
        json_counter = 0
        json_df = {"convoy": []}
        xml_counter = 0
        xml_df = []

        for _i, z in enumerate(nvm['score']):
            if int(z) > 3:
                # to json
                json_counter += 1
                k = my_df['convoy'][_i]
                json_df["convoy"].append(k)
                json_df['convoy'][-1].pop('score')
                # json_df["convoy"][_i] = k
            else:
                # to xml
                xml_counter += 1
                xk = df_for_xml[_i]
                xml_df.append(xk)
                xml_df[-1].pop('score')

        cur.close()
        conn.close()
        # пытаемся впихнуть в жсон
        with open(file.replace(".s3db", ".json"), 'w') as opened_file:
            json.dump(json_df, opened_file)
        # пишем результат и ретёрн
        if json_counter != 1:
            print(f'{json_counter} vehicles were saved into {file.replace(".s3db", ".json")}')
        else:
            print(f'{json_counter} vehicle was saved into {file.replace(".s3db", ".json")}')
        s3db_to_xml(file, xml_df, xml_counter)
        return file.replace('.s3db', '.json')


    def s3db_to_xml(file, _xml_df, _counter):
        with open(file.replace(".s3db", ".xml"), 'w') as opened_file:
            _xml = dicttoxml(_xml_df, custom_root='convoy',
                             attr_type=False, item_func=lambda x: 'vehicle')
            good_xml = str(_xml)[2:-1].replace('<?xml version="1.0" encoding="UTF-8" ?>', '')
            opened_file.write(good_xml)
        if _counter != 1:
            print(f'{_counter} vehicles were saved into {file.replace(".s3db", ".xml")}')
        else:
            print(f'{_counter} vehicle was saved into {file.replace(".s3db", ".xml")}')


    # ------- S T A R T -------
    input_file_name = input('Input file name\n')
    # хлсх ? = в ксв
    if '.xlsx' in input_file_name:
        csv_file_name = xlsx_to_csv(input_file_name)
    else:
        csv_file_name = input_file_name
    # не чекед ксв ? = в чекед
    if '[CHECKED].csv' not in csv_file_name and '.csv' in csv_file_name:
        checked_file_name = check_csv(csv_file_name)
    else:
        checked_file_name = csv_file_name
    # не с3дб ? = в с3дб
    if '[CHECKED].csv' in checked_file_name:
        s3db_file_name = csv_to_s3db(checked_file_name)
    else:
        s3db_file_name = checked_file_name
    # в жсон
    if '.s3db' in s3db_file_name:
        json_file_name = s3db_to_json_and_xml(s3db_file_name)
    else:
        json_file_name = s3db_file_name

