import os
import datetime
import psycopg2
import fitbit, time

class SensorProcess():
    def __init__(self):
        self.dp = DBProcess()
        # メモしたID等
        self.CLIENT_ID = os.environ["CLIENT_ID"]
        self.CLIENT_SECRET = os.environ["CLIENT_SECRET"]
        self.ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
        self.REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

        # ID等の設定
        self.client = fitbit.Fitbit(self.CLIENT_ID,                                                                self.CLIENT_SECRET,
                            access_token=self.ACCESS_TOKEN,
                            refresh_token=self.REFRESH_TOKEN,
                            )

    def getDataFromFitbit(self):
        count = 0 # 10000レコード(2000回)のカウントに使う
        # data_from_fitbit = []
        while count < 2000: # 2000*2/60 = 66時間分．
            #現在の年月日，時刻
            today = datetime.datetime.now()
            today_before_minutes = today + datetime.timedelta(minutes=-5)

            #消費カロリー関連のデータ取得
            raw_data = self.client.intraday_time_series("activities/heart", base_date="today", detail_level="1min", start_time="{0}:{1}".format(today_before_minutes.hour, today_before_minutes.minute), end_time="{0}:{1}".format(datetime.datetime.now().hour, datetime.datetime.now().minute))
            list_of_dict_cal_time = raw_data["activities-heart-intraday"]["dataset"]
            len_dicts_cal_time = len(list_of_dict_cal_time)

            #カロリーのリストを作成
            calories_list =[]
            for i in range(len_dicts_cal_time):
                tmp = list_of_dict_cal_time[i]["value"]
                tmp = float(f"{tmp:.2f}") #小数点2桁まで
                calories_list.append(tmp)

            #時間のリスト(str)を作成
            str_time_list = []
            for i in range(len_dicts_cal_time):
                tmp = list_of_dict_cal_time[i]["time"]
                str_time_list.append(tmp)  #["00:00:00"]

            #上で作った文字列の時刻リストをdatetime型に
            str_split_time = []
            for i in range(len_dicts_cal_time):
                tmp = str_time_list[i].split(":")
                str_split_time.append(tmp) # [["00", "00", "00"], ・・]
            #ここでdatetimeに変更
            datetime_time = []
            for i in range(len_dicts_cal_time):
                # 「時」について，グリニッジ標準時との時差9時間を加算している．
                datetime_time.append(datetime.datetime(int(today.year), int(today.month), int(today.day), int(str_split_time[i][0])+9, int(str_split_time[i][1]), int(str_split_time[i][2])))

            #calories_listとdatetime_timeから辞書を作成，キー設定
            #辞書のリスト作成
            '''
            for i in range(len_dicts_cal_time):
                tmp = {"datetime": datetime_time[i], "calorie": calories_list[i]}
                tmp["user_id"] = "a001" # user_id（固定）の追加
                self.dp.dbInsert(tmp)
                # data_from_fitbit.append(tmp)
            '''
            tmp = {"user_id":"a001", "datetime": datetime_time[len_dicts_cal_time-1], "calorie": calories_list[len_dicts_cal_time-1]}
            print("\n\n\n\n\n\n\n\ntmp : {0}\n\n\n\n\n\n\n".format(tmp))
            self.dp.dbInsert(tmp)
            count += 1
            time.sleep(120)

'''
http://h2shiki.hateblo.jp/entry/2016/05/05/210738
'''
class DBProcess():
    def __init__(self):
        self.tableName = "nagara"
        self.DB_HOSTNAME = os.environ["DB_HOSTNAME"]
        self.DB_DATABASE = os.environ["DB_DATABASE"]
        self.DB_PORT = os.environ["DB_PORT"]
        self.DB_USER = os.environ["DB_USER"]
        self.DB_PASSWORD = os.environ["DB_PASSWORD"]
        #self.attrs = ["id", "user_id", "calorie", "heart_rate", "steps_num", "temp", "datetime"]
    
    def getDBConn(self):
        return psycopg2.connect(
            host = self.DB_HOSTNAME,
            database = self.DB_DATABASE,
            port = self.DB_PORT,
            user = self.DB_USER,
            password = self.DB_PASSWORD
        )
    
    '''
    def getMaxID(self):
        with self.getDBConn() as conn:
            with conn.cursor() as cursor:
                sql = "select max(id) from {0};".format(self.tableName)
                cursor.execute(sql)
                result = cursor.fetchone()
                (currentID,) = result
        return currentID
    '''

    def dbInsert(self, record):
        '''
        [引数]
        ●record
        ・(dict){"attr1":data1, "attr2":data2,...}
        ・シリアルプライマリーキーであるidは引数にしない！
        ・idはgetMaxID()からから取得する．
        [変更]
        ・datetimeはSQLのnow()から，ではなく引数に含めて受け取る．
        '''
        attrs = ""
        datas = ""
        i = 0
        for attr,data in record.items():
            if i<len(record)-1:
                attrs += str(attr) + ","
                datas += "{0},".format(str(data)) if attr!="user_id" and attr!="datetime" else "'{0}',".format(data)
                i += 1
            else:
                attrs += str(attr)
                datas += "{0}".format(str(data)) if attr!="user_id" and attr!="datetime" else "'{0}'".format(data)

        with self.getDBConn() as conn:
            with conn.cursor() as cursor:
                '''
                #dbnum = self.getMaxID()
                #print("\n\n\n\n\n\n\n\ndbMax : {0}\n\n\n\n\n\n\n".format(dbnum)) # herokuのlogsで確認！！
                id = 0 if not dbnum else dbnum+1
                sql = "insert into {0}(id,{1}) values({2},{3})".format(self.tableName, attrs, id, datas)
                '''
                sql = "insert into {0}({1}) values({2})".format(self.tableName, attrs, datas)
                cursor.execute(sql)
                conn.commit()
    
    def dbSelect(self, attr):
        '''
        [引数]
        ●attr
        ・(str)"項目1,項目2,..."
        ・すべての項目を取得する場合は"*"のみ．
        [戻り値]
        ●(list)[data1,data2,...]
        ・対応するアトリビュートのみ．
        '''
        with self.getDBConn() as conn:
            with conn.cursor() as cursor:
                sql = "select {0} from {1} order by id asc".format(attr, self.tableName)
                cursor.execute(sql)
                result = cursor.fetchall()
        return result