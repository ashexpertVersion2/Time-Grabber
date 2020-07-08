#!/usr/bin/env python
import sys
import sqlite3
import datetime

date_format = "%Y-%m-%d %H:%M:%S.%f"

# sqlite3.connect("timeTable.sqlite3")

# command = sys.argv[1]
class Handler:
    def __init__(self, databasename="timeTable.sqlite3"):
        self.con = sqlite3.connect(databasename, isolation_level=None)
        self.cursor = self.con.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS time_table (
        id INTEGER AUTOINC,
        datetime TIMESTAMP,
        type TEXT,
        PRIMARY KEY (id))""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS extra_time (
        id INTEGER AUTOINC,
        datetime TIMESTAMP,
        time_in_sec INTEGER,
        PRIMARY KEY (id))""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS lower_time (
        id INTEGER AUTOINC,
        datetime TIMESTAMP,
        time_in_sec INTEGER,
        PRIMARY KEY (id))""")

    def __del__(self):
        # self.con.commit()
        self.con.close()

    def _is_started(self):
        # start of day!
        day_start, date = self._is_day_started()
        if not day_start:
            return False

        self.cursor.execute(
            "SELECT type FROM time_table where (type='start' or type='stop') and datetime >= ? ORDER BY datetime DESC LIMIT 1",
            (date,))
        row = self.cursor.fetchall()

        if len(row) == 0 or row[0][0] != "start":
            return False
        return True

    def _is_day_started(self)->(bool,datetime.datetime):
        self.cursor.execute(
            "SELECT type, datetime FROM time_table where type='day-start' or type='day-stop' ORDER BY datetime DESC LIMIT 1")
        row = self.cursor.fetchall()

        if len(row) == 0 or row[0][0] != "day-start":
            return False, None
        return True, datetime.datetime.strptime(row[0][1], date_format)

    def start_day(self):
        if self._is_day_started()[0]:
            print("ERROR: your day is already started")
            return 1
        self.cursor.execute("""INSERT INTO time_table (datetime, type) VALUES(?, ?)""",
                            (datetime.datetime.now(), "day-start"))
        print("your day started don't forget coffee")
        return 0

    def stop_day(self):
        if not self._is_day_started()[0]:
            print("your day is not started")
            return 1

        if self._is_started():
            print("you have a started task and im gonna close it!")
            self.stop()

        self.cursor.execute("""INSERT INTO time_table (datetime, type) VALUES(?, ?)""",
                            (datetime.datetime.now(), "day-stop"))
        print("your day stopped don't forget your cigarette!")
        return 0

    def start(self):
        if not self._is_day_started()[0]:
            print("your day is not started do you want to start it?[Y/n]")
            inp = input()
            if inp.lower() in ("", "y", "yes"):
                self.start_day()
            elif inp.lower() in ("n", "no"):
                print("ok")
                return 0
            else:
                print("WTF?")
                return 1

        if self._is_started():
            print("ERROR: your task is already started")
            return 1
        self.cursor.execute("""INSERT INTO time_table (datetime, type) VALUES(?, ?)""",
                            (datetime.datetime.now(), "start"))
        print("your task started successfully! rise and shine :)")
        return 0

    def stop(self):
        if not self._is_started():
            print("ERROR: you don't have any started task!")
            if not self._is_day_started()[0]:
                print("you haven't even started your day... do you even science bro????")
            return 1
        self.cursor.execute("""INSERT INTO time_table (datetime, type) VALUES(?, ?)""",
                            (datetime.datetime.now(), "stop"))
        print("your task stopped successfully! go for a relax :)")
        return 0

    def run(self, com):
        if com[0] == "start":
            return self.start()
        elif com[0] == "stop":
            return self.stop()
        elif com[0] == "startday":
            self.start_day()
        elif com[0] == "stopday":
            self.stop_day()
        elif com[0] == "eval":
            if "--ago" in com:
                return self.eval(int(com[com.index("--ago") + 1]))
            return self.eval(1)
        elif com[0] == "add":
            return self.add_time(com[1:])
        elif com[0] == "lower":
            return self.lower_time(com[1:])
        elif com[0] == "status":
            return self.status()
        elif com[0] == "undo":
            return self.undo()
        elif com[0] == "help":
            print("""
usage:
tg [command] [args] [--database {database_anme}]
commands:
  startday: start the day
  stopday: stop the day
  start: start the timer for today
  stop: stop timer for today
  eval:
      evaluate total time for a specified day
      args:
        --ago {number_of_day}
          eval for number_of_day (s) ago from now
      note: if no args is specified it will eval total time for today
  add:
      add some extra times (usable for meetings, daily, ...)
        args:
          {seconds}{s/S}
          {minutes}{m/M}
          {hour}{h/H}
      example:
        add 10s
        add 10h
  lower:
      remove some time from total time (usable for error handling)
        args:
          (like add)
  status:
      print summary of status
  undo:
      undo the last operation
  help:
      print this guide!
""")
        else:
            print("error: typo in command!")
            return 1

    def eval(self, ago):
        today_start_row = self.cursor.execute(
            f"SELECT datetime FROM time_table where type='day-start' ORDER BY datetime DESC LIMIT {ago}").fetchall()
        today_start = datetime.datetime.fromisoformat(today_start_row[-1][0]) if len(today_start_row) != 0 else datetime.datetime.now()
        today_end_row = self.cursor.execute(
            f"SELECT datetime FROM time_table where type='day-stop' ORDER BY datetime DESC LIMIT {ago}").fetchall()
        today_end = datetime.datetime.fromisoformat(today_end_row[-1][0]) if len(today_end_row) != 0 else datetime.datetime.now()

        if today_start > today_end:  # probably we have a open day
            if ago > 1:
                today_end_row = self.cursor.execute(
                    f"SELECT datetime FROM time_table where type='day-stop' ORDER BY datetime DESC LIMIT {ago-1}").fetchall()
                today_end = today_end_row[-1][0] if len(today_end_row) != 0 else datetime.datetime.now()
            else:
                today_end = datetime.datetime.now()
            print("calculating time for", today_start, " till ", today_end)

        # stop time
        self.cursor.execute("SELECT datetime FROM time_table WHERE datetime > ? AND type = 'stop' AND datetime < ?",
                            (today_start, today_end))
        stop_rows = self.cursor.fetchall()
        # print(rows)
        stop = datetime.timedelta(0, 0, 0, 0, 0, 0, 0)
        for it in stop_rows:
            stop += datetime.datetime.fromisoformat(it[0]) - datetime.datetime(1900, 1, 1)
        # start time
        self.cursor.execute("SELECT datetime FROM time_table WHERE datetime > ? AND type = 'start' AND datetime < ?",
                            (today_start, today_end))
        start_rows = self.cursor.fetchall()

        start = datetime.timedelta(0, 0, 0, 0, 0, 0, 0)
        for it in start_rows:
            start += datetime.datetime.fromisoformat(it[0]) - datetime.datetime(1900, 1, 1)

        # extra time
        self.cursor.execute("SELECT SUM(time_in_sec) FROM extra_time WHERE datetime > ? AND datetime < ?",
                            (today_start, today_end))
        resp = self.cursor.fetchall()

        if resp[0][0] is None:
            extra_times = datetime.timedelta(0)
        else:
            extra_times = datetime.timedelta(seconds=resp[0][0])

        # lower time
        self.cursor.execute("SELECT SUM(time_in_sec) FROM lower_time WHERE datetime > ? AND datetime < ?",
                            (today_start, today_end))
        resp = self.cursor.fetchall()

        if resp[0][0] is None:
            lower_times = datetime.timedelta(0)
        else:
            lower_times = datetime.timedelta(seconds=resp[0][0])

        if self._is_started():
            print(stop - start + extra_times - lower_times + (datetime.datetime.now() - datetime.datetime(1900, 1, 1)))
        else:
            print(stop - start + extra_times - lower_times)
        return 0

    def add_time(self, cmd):
        if not self._is_day_started()[0]:
            print("no active day!")
            return 1
        time = int(cmd[0][:-1])
        if cmd[0][-1] in ['m', 'M']:
            time *= 60
        if cmd[0][-1] in ['h', 'H']:
            time *= 60 * 60
        self.cursor.execute("INSERT INTO extra_time (datetime, time_in_sec) VALUES(?, ?)",
                            (datetime.datetime.now(), time))
        print("added", cmd[-1])
        return 0

    def status(self):
        print("you are running!")
        print("total time of today:")
        self.eval(1)
        return 0

    def lower_time(self, cmd):
        if not self._is_day_started()[0]:
            print("no active day!")
            return 1

        time = int(cmd[0][:-1])
        if cmd[0][-1] in ['m', 'M']:
            time *= 60
        if cmd[0][-1] in ['h', 'H']:
            time *= 60 * 60
        self.cursor.execute("INSERT INTO lower_time (datetime, time_in_sec) VALUES(?, ?)",
                            (datetime.datetime.now(), time))
        print("lowered", cmd[-1])
        return 0

    def undo(self):
        # select last thing that has done
        max_datetime = self.cursor.execute("SELECT MAX(datetime) FROM time_table;").fetchall()[0][0]
        # max_datetime_f = datetime.datetime.strptime(max_datetime,date_format)
        max_rec = self.cursor.execute("SELECT type,datetime FROM time_table WHERE datetime = ?", (max_datetime,)).fetchall()[0]
        print(f"undoing {max_rec[0]} at {max_rec[1]}")
        self.cursor.execute("DELETE FROM time_table WHERE datetime = ?", (max_datetime,))


args = sys.argv
if "--database" in args:
    h = Handler(args[args.index("--database") + 1])
    args.pop(args.index("--database") + 1)
    args.pop(args.index("--database"))
else:
    h = Handler()
res = h.run(args[1:])
del h
exit(res)
