# dialog.py

"""Dialog-style application."""
import ssl
import sys
import sqlite3 as sl
from datetime import datetime as dt
import smtplib

from PyQt6.QtWidgets import (
    QApplication,
    QLineEdit,
    QVBoxLayout,
    QGridLayout,
    QComboBox,
    QWidget,
    QPushButton,
    QLabel,
)

gapp = None


def execute_sql_query(conn, query, values=None):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param query: a CREATE TABLE statement
    :return:
    """
    c = None
    try:
        c = conn.cursor()
        if values is not None:
            c.execute(query, values)
        else:
            c.execute(query)
    except sl.Error as e:
        print(e)
        return None
    conn.commit()
    return c.fetchall()


def init_db():
    conn = sl.connect('my-test.db')
    sql_create_projects_table = """ CREATE TABLE IF NOT EXISTS stocktaking (
                                        box_no TEXT KEY,
                                        take_date TEXT NOT NULL,
                                        dead INTEGER NOT NULL,
                                        transferred INTEGER NOT NULL,
                                        slaughtered INTEGER NOT NULL
                                    ); """
    if conn is not None:
        execute_sql_query(conn, sql_create_projects_table)
        return conn
    else:
        print("Error! cannot create the database connection.")


class MainWindow(QWidget):
    sector_window = None
    select_sector_button = None
    backup_button = None
    select_sector_combo_box = None
    conn = None

    class SectorWindow(QWidget):
        parent_window = None
        entries_in_page = 5
        sector_no = None
        button_next_page = None
        button_previous_page = None
        button_ok = None
        back_button = None
        page_number = None
        qlable_box_num_list = None
        input_box_num_show = None
        input_box_slaughter_list = None
        input_box_transferred_list = None
        input_box_death_list = None
        conn = None

        def __init__(self, sector_no, connection, parent_window_):
            super(MainWindow.SectorWindow, self).__init__()
            self.resize(400, 300)

            # connection
            if connection is None:
                print("ERROR : no connection to data base for sector")
                return
            self.conn = connection
            self.parent_window = parent_window_
            self.page_number = 0
            self.sector_no = sector_no
            self.input_box_slaughter_list = list()
            self.input_box_death_list = list()
            self.input_box_transferred_list = list()
            self.qlable_box_num_list = list()
            layout = QGridLayout()
            self.setLayout(layout)

            self.back_button = QPushButton()
            self.back_button.setText("חזור")
            self.back_button.clicked.connect(self.parent_window.returned_from_sector)

            self.button_next_page = QPushButton()
            self.button_next_page.setText("הבא")
            self.button_next_page.clicked.connect(self.inc_page)

            self.button_previous_page = QPushButton()
            self.button_previous_page.setText("לפני")
            self.button_previous_page.clicked.connect(self.dec_page)

            self.button_ok = QPushButton()
            self.button_ok.setText("בצע")
            self.button_ok.clicked.connect(self.insert_data)

            qlable_sector_name = QLabel()
            qlable_sector_name.setText("sector " + sector_no)
            layout.addWidget(qlable_sector_name, 0, 2)
            layout.addWidget(self.back_button, 0, 0)

            self.input_box_num_show = QLineEdit()
            self.input_box_num_show.textChanged.connect(self.show_page_num)
            layout.addWidget(self.input_box_num_show, 0, 3)

            # Label
            for i in range(self.entries_in_page):
                input_box_death = QLineEdit(self)
                input_box_death.setText(" ")
                self.input_box_death_list.append(input_box_death)

                input_box_transferred = QLineEdit(self)
                input_box_transferred.setText(" ")
                self.input_box_transferred_list.append(input_box_transferred)

                input_box_slaughtered = QLineEdit(self)
                input_box_slaughtered.setText(" ")
                self.input_box_slaughter_list.append(input_box_slaughtered)

                qlable_box_no = QLabel("box number " + (self.page_number + i).__str__())
                self.qlable_box_num_list.append(qlable_box_no)

                layout.addWidget(qlable_box_no, i + 1, 0)
                layout.addWidget(input_box_death, i + 1, 1)
                layout.addWidget(input_box_transferred, i + 1, 2)
                layout.addWidget(input_box_slaughtered, i + 1, 3)

            layout.addWidget(self.button_previous_page, self.entries_in_page + 2, 1)
            layout.addWidget(self.button_ok, self.entries_in_page + 2, 2)
            layout.addWidget(self.button_next_page, self.entries_in_page + 2, 3)

            self.update_qlable_box_numbers()

        def update_qlable_box_numbers(self):
            for box_no in range(self.entries_in_page):
                self.qlable_box_num_list[box_no].setText(
                    "box number " + (int(self.page_number * self.entries_in_page + box_no)).__str__())
                current_death_query = """ SELECT dead, transferred, slaughtered FROM stocktaking
                                            WHERE take_date IN 
                                            ( SELECT MAX(take_date) FROM stocktaking
                                              WHERE box_no = ?
                                            )
                                            AND box_no = ?;
                                            """
                box_info = execute_sql_query(self.conn, current_death_query,
                                             (self.sector_no + str(box_no + self.page_number * self.entries_in_page),
                                              self.sector_no + str(box_no + self.page_number * self.entries_in_page)
                                              ))

                if len(box_info) > 0:
                    self.input_box_death_list[box_no].setText(str(box_info[0][0]))
                    self.input_box_transferred_list[box_no].setText(str(box_info[0][1]))
                    self.input_box_slaughter_list[box_no].setText(str(box_info[0][2]))

                else:
                    self.input_box_death_list[box_no].setText(" ")
                    self.input_box_transferred_list[box_no].setText(" ")
                    self.input_box_slaughter_list[box_no].setText(" ")

        def inc_page(self):
            self.page_number = self.page_number + 1
            self.update_qlable_box_numbers()

        def dec_page(self):
            if self.page_number >= 1:
                self.page_number = self.page_number - 1
                self.update_qlable_box_numbers()

        def insert_data(self):
            check_table_query = """ CREATE TABLE IF NOT EXISTS stocktaking (
                                                box_no TEXT,
                                                take_date TEXT NOT NULL,
                                                dead INTEGER NOT NULL,
                                                transferred INTEGER NOT NULL,
                                                slaughtered INTEGER NOT NULL
                                            ); """
            try:
                self.conn.cursor().execute(check_table_query)
            except sl.Error as e:
                print(e)
                return

            self.conn.commit()

            for i in range(self.entries_in_page):
                entry_index = i + self.page_number * self.entries_in_page
                insert_entries_query = """ INSERT INTO stocktaking (box_no,take_date, dead, transferred,slaughtered)
                                                VALUES (?, ?, ?, ?, ?); """
                box_curr_info = [self.input_box_death_list[i].text(),
                                 self.input_box_transferred_list[i].text(),
                                 self.input_box_slaughter_list[i].text()]
                if " " in box_curr_info:
                    print("not now")
                    continue
                values = (str(self.sector_no) + str(entry_index),
                          str(dt.now()),
                          int(box_curr_info[0]),
                          int(box_curr_info[1]),
                          int(box_curr_info[2])
                          )
                execute_sql_query(self.conn, insert_entries_query, values)

        def show_page_num(self):
            try:
                page_num_to_show = int(int(self.input_box_num_show.text()) / self.entries_in_page)
            except ValueError:
                self.input_box_num_show.setText(self.input_box_num_show.text()[:-1])
                return

            self.page_number = page_num_to_show
            self.update_qlable_box_numbers()

    def send_in_mail(self):
        # TODO : check the best way to send mail via python
        port = 587  # For starttls
        smtp_server = "smtp.gmail.com"
        sender_email = "stocktakingarraf@gmail.com"
        receiver_email = "arraf46@gmail.com"
        password = "lina0410L"
        message = """\
        Subject: Hi there

        This message is sent from Python."""

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

    def __init__(self, connection):
        super().__init__()

        # connection
        if conn is None:
            print("ERROR : no connection to data base")
            return
        self.conn = connection

        # set window aspects
        self.sector_window = None
        self.setWindowTitle("stocktaking")
        self.setLayout(QVBoxLayout())

        # widgets
        sector_no_lable = QLabel("מחלקה מס׳")
        self.select_sector_combo_box = QComboBox()
        self.cb = self.select_sector_combo_box
        self.cb.addItems(["A", "B", "C"])

        self.select_sector_button = QPushButton()
        self.select_sector_button.setText("בחר")
        self.select_sector_button.clicked.connect(self.select_sector_button_clicked)

        self.backup_button = QPushButton()
        self.backup_button.setText("שלח במייל")
        self.backup_button.clicked.connect(self.send_in_mail)

        # adding  to layout
        self.layout().addWidget(sector_no_lable)
        self.layout().addWidget(self.cb)
        self.layout().addWidget(self.select_sector_button)
        self.layout().addWidget(self.backup_button)
        self.show()

    def select_sector_button_clicked(self):
        self.sector_window = self.SectorWindow(str(self.select_sector_combo_box.currentText()), conn, self)
        self.sector_window.show()
        self.hide()

    def returned_from_sector(self):
        self.sector_window.close()
        del self.sector_window
        self.sector_window = None
        self.show()


if __name__ == "__main__":
    conn = init_db()
    if conn is None:
        exit(0)
    gapp = QApplication([])
    g_main_window = MainWindow(conn)
    g_main_window.show()
    sys.exit(gapp.exec())
