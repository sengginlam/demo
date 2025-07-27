from openpyxl import load_workbook
from datetime import datetime
from typing import List, Dict
from os import path
from itertools import chain
import numpy as np
import MySQLdb


SEED = 45616113
STOCKS_SIZE = 5
DAILY_EXEC = 1000
DAILY_NUM = (1E+5, 1E+8)
HOST = "127.0.0.1"
PORT = 3306
DATABASE = "demo"
USER = "root"
PASSWORD = "123456"
CHARSET = "utf8mb4"
TABLE_DATA = "Data"
TABLE_DETAIL = "Detail"


class Database():
    def __init__(self):
        SQL_CREATE_USER = '''
            CREATE TABLE IF NOT EXISTS `Users` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `username` varchar(45) NOT NULL,
            `password` char(32) NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
            UNIQUE INDEX `username_UNIQUE` (`username` ASC) VISIBLE
            )
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4;
        '''
        SQL_CREATE_DATA = '''
            CREATE TABLE IF NOT EXISTS `Data` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `stock_symbol` INT NOT NULL,
            `date` INT NOT NULL,
            `opening_price` DECIMAL(6,2) NOT NULL,
            `closing_price` DECIMAL(6,2) NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
            )
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4;
        '''
        SQL_CREATE_DETAIL = '''
            CREATE TABLE IF NOT EXISTS `Detail` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `stock_symbol` INT NOT NULL,
            `date` INT NOT NULL,
            `execution_price` DECIMAL(6,2) NOT NULL,
            `number_of_shared_traded` INT NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE
            )
            ENGINE = InnoDB
            DEFAULT CHARACTER SET = utf8mb4;
        '''
        self._conn = MySQLdb.connect(host=HOST, port=PORT, db=DATABASE, user=USER, password=PASSWORD, charset=CHARSET)
        self._curs = self._conn.cursor()
        self._curs.execute(SQL_CREATE_DATA)
        self._curs.execute(SQL_CREATE_DETAIL)
        self._curs.execute(SQL_CREATE_USER)
        self._conn.commit()
        self._curs.execute("SELECT `username` FROM `Users`")
        res = self._curs.fetchall()
        if len(res)==0:
            self._curs.execute("INSERT INTO `Users`(`username`, `password`) VALUES('user', 'ee11cbb19052e40b07aac0ca060c23ee');")
            self._conn.commit()
    
    def insert(self, table:str, data:List[Dict[str, str|float]]) -> None:
        SQL_INSERT_DATA = '''
            INSERT INTO `Data`(
            `stock_symbol`, 
            `date`, 
            `opening_price`,
            `closing_price`
            ) 
            VALUES(
            %(stock_symbol)s, 
            %(date)s, 
            %(opening_price)s,
            %(closing_price)s
            );
        '''
        SQL_INSERT_DETAIL = '''
            INSERT INTO `Detail`(
            `stock_symbol`, 
            `date`, 
            `execution_price`,
            `number_of_shared_traded`
            ) 
            VALUES(
            %(stock_symbol)s, 
            %(date)s, 
            %(execution_price)s,
            %(number_of_shared_traded)s
            );
        '''
        try:
            if table==TABLE_DATA:
                self._curs.executemany(SQL_INSERT_DATA, data)
            elif table==TABLE_DETAIL:
                self._curs.executemany(SQL_INSERT_DETAIL, data)
            else:
                raise TypeError
            self._conn.commit()
        except:
            self._conn.rollback()
    
    def close(self)-> None:
        self._conn.close()

def load_trading_days() -> np.ndarray:
    def iter_days():
        for row in book.active.values:
            try:
                date = int(row[0])
                if date<now:
                    yield date
            except:
                pass
    now = datetime.now()
    now = now.year*10000+now.month*100+now.day
    p = path.join(path.dirname(__file__), "trading_days.xlsx")
    book = load_workbook(p, read_only=True)
    days = np.array(list(iter_days()))
    trading_days = np.tile(days, (STOCKS_SIZE, 1))
    book.close()
    return trading_days

def simulate(length:int) -> List[np.ndarray]:
    np.random.seed(SEED)
    mean = np.random.randint(low=100, high=10001, size=STOCKS_SIZE)
    mean = mean.astype(np.float64)/100
    std_dev = np.random.randint(low=500, high=5001, size=STOCKS_SIZE)
    std_dev = std_dev.astype(np.float64)/10000
    opening = np.random.normal(
            mean.reshape((-1, 1)), 
            std_dev.reshape((-1, 1)), 
            (STOCKS_SIZE, length+1)
        )
    opening_prev = opening[:, :-1]
    opening_curr = opening[:, 1:]
    lower_20 = opening_prev*0.8
    upper_20 = opening_prev*1.2    
    opening = np.clip(opening_curr, lower_20, upper_20)
    exec_shape = (STOCKS_SIZE, length, DAILY_EXEC)
    execution = np.random.normal(
            np.repeat(opening, DAILY_EXEC).reshape(exec_shape), 
            np.repeat(std_dev, length*DAILY_EXEC).reshape(exec_shape), 
            exec_shape
        )
    lower_10 = np.repeat(opening_prev*0.9, DAILY_EXEC).reshape(exec_shape)
    upper_10 = np.repeat(opening_prev*1.1, DAILY_EXEC).reshape(exec_shape)
    execution = np.clip(execution, lower_10, upper_10)
    closing = execution[:, :, 0]
    nm = np.random.randint(*DAILY_NUM, (STOCKS_SIZE, length, DAILY_EXEC*2))
    number_mean = nm[:, :, ::2]
    number_std_dev = nm[:, :, 1::2]
    number = np.random.normal(
            number_mean, 
            number_std_dev, 
            exec_shape
        ).astype(np.int64)
    number = np.clip(number, *DAILY_NUM).astype(np.int64)
    return [np.round(opening, 2), np.round(closing, 2), np.round(execution, 2), number]

def main():
    KEYS_DATA = ("stock_symbol", "date", "opening_price", "closing_price")
    KEYS_DETAIL = ("stock_symbol", "date", "execution_price", "number_of_shared_traded")
    trading_days = load_trading_days()
    td = trading_days.shape[-1]
    symbol = np.repeat(tuple(i*100000 for i in range(1, 6, 1)), td).reshape((STOCKS_SIZE, -1))
    opening, closing, execution, number = simulate(td)
    data = np.stack((symbol, trading_days, opening, closing), 2).tolist()
    data = list(map(lambda v: dict(zip(KEYS_DATA, v)), list(chain.from_iterable(data))))
    exec_shape = (STOCKS_SIZE, td, DAILY_EXEC)
    detail = np.stack(
        (
            np.repeat(symbol, DAILY_EXEC).reshape(exec_shape), 
            np.repeat(trading_days, DAILY_EXEC).reshape(exec_shape), 
            execution, 
            number
        ), 
        axis=3
    ).tolist()
    detail = list(map(lambda v: dict(zip(KEYS_DETAIL, v)), list(chain.from_iterable(chain.from_iterable(detail)))))
    db = Database()
    db.insert(TABLE_DATA, data)
    db.insert(TABLE_DETAIL, detail)
    db.close()


if __name__=="__main__":
    home = path.dirname(__file__)
    if not path.exists(path.join(home, "init_success")):
        main()
        with open(path.join(home, "init_success"), "wt") as file:
            pass