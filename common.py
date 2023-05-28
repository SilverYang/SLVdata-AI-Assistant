# coding=UTF-8
# import os
from pathlib import Path

class CommonFunction(object):
    def __init__(self):
        self.__conn = None
        self.__cursor = None

    # 取用户的ACCOUNT-ID and API-KEY
    def get_account_id_key(self, settings_file):
        account_id = ''
        api_key = ''
        # if os.path.exists(settings_file):
        if Path.exists(settings_file):
            f = open(settings_file, 'r')
            for line in f.readlines():
                if line[0:11] == 'ACCOUNT-ID=':
                    account_id = line[11:].strip()
                if line[0:8] == 'API-KEY=':
                    api_key = line[8:].strip()
        return account_id, api_key


def main():
    pass


if __name__ == "__main__":
    main()
