import pymysql
import datetime
import json
import boto3
from botocore.response import StreamingBody
from decimal import Decimal

s3 = boto3.client('s3')


def uploadImage(file, key, content):
    bucket = 'io-pm'
    contentType = ''

    if type(file) == StreamingBody:
        contentType = content

    if file:
        # print('if file', file, bucket, key)
        filename = f'https://s3-us-west-1.amazonaws.com/{bucket}/{key}'
        upload_file = s3.put_object(
            Bucket=bucket,
            Body=file.read(),
            Key=key,
            ACL='public-read',
            ContentType=contentType
        )

        return filename
    return None


def connect():
    conn = pymysql.connect(
        host='io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com',
        port=3306,
        user='admin',
        passwd='prashant',
        db='space',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return DatabaseConnection(conn)


def serializeJSON(unserialized):
    # print(unserialized, type(unserialized))
    if type(unserialized) == list:
        # print("in list")
        serialized = []
        for entry in unserialized:
            serializedEntry = serializeJSON(entry)
            serialized.append(serializedEntry)
        return serialized
    elif type(unserialized) == dict:
        # print("in dict")
        serialized = {}
        for entry in unserialized:
            serializedEntry = serializeJSON(unserialized[entry])
            serialized[entry] = serializedEntry
        return serialized
    elif type(unserialized) == datetime.datetime:
        # print("in date")
        return str(unserialized)
    elif type(unserialized) == bytes:
        # print("in bytes")
        return str(unserialized)
    elif type(unserialized) == Decimal:
        # print("in Decimal")
        return str(unserialized)
    else:
        # print("in else")
        return unserialized


class DatabaseConnection:
    def __init__(self, conn):
        self.conn = conn

    def disconnect(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

    def execute(self, sql, args=[], cmd='get'):
        # print("In execute.  SQL: ", sql)
        # print("In execute.  args: ",args)
        # print("In execute.  cmd: ",cmd)
        response = {}
        try:
            with self.conn.cursor() as cur:
                # print('IN EXECUTE')
                if len(args) == 0:
                    # print('execute', sql)
                    cur.execute(sql)
                else:
                    cur.execute(sql, args)
                formatted_sql = f"{sql} (args: {args})"
                # print(formatted_sql)
                    

                if 'get' in cmd:
                    # print('IN GET')
                    result = cur.fetchall()
                    result = serializeJSON(result)
                    # print('RESULT GET')
                    response['message'] = 'Successfully executed SQL query'
                    response['code'] = 200
                    response['result'] = result
                    # print('RESPONSE GET')
                elif 'post' in cmd:
                    # print('IN POST')
                    self.conn.commit()
                    response['message'] = 'Successfully committed SQL query'
                    response['code'] = 200
                    # print('RESPONSE POST')
        except Exception as e:
            print('ERROR', e)
            response['message'] = 'Error occurred while executing SQL query'
            response['code'] = 500
            response['error'] = e
            print('RESPONSE ERROR', response)
        return response

    def select(self, tables, where={}, cols='*'):
        response = {}
        try:
            sql = f'SELECT {cols} FROM {tables}'
            for i, key in enumerate(where.keys()):
                if i == 0:
                    sql += ' WHERE '
                sql += f'{key} = %({key})s'
                if i != len(where.keys()) - 1:
                    sql += ' AND '

            response = self.execute(sql, where, 'get')
        except Exception as e:
            print(e)
        return response

    def insert(self, table, object):
        response = {}
        try:
            sql = f'INSERT INTO {table} SET '
            for i, key in enumerate(object.keys()):
                sql += f'{key} = %({key})s'
                if i != len(object.keys()) - 1:
                    sql += ', '
            # print(sql)
            # print(object)
            response = self.execute(sql, object, 'post')
        except Exception as e:
            print(e)
        return response

    def update(self, table, primaryKey, object):
        response = {}
        try:
            sql = f'UPDATE {table} SET '
            print(sql)
            for i, key in enumerate(object.keys()):
                sql += f'{key} = %({key})s'
                if i != len(object.keys()) - 1:
                    sql += ', '
            sql += f' WHERE '
            print(sql)
            for i, key in enumerate(primaryKey.keys()):
                sql += f'{key} = %({key})s'
                object[key] = primaryKey[key]
                if i != len(primaryKey.keys()) - 1:
                    sql += ' AND '
            print(sql, object)
            response = self.execute(sql, object, 'post')
            print(response)
        except Exception as e:
            print(e)
        return response

    def delete(self, sql):
        response = {}
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql)

                self.conn.commit()
                response['message'] = 'Successfully committed SQL query'
                response['code'] = 200
                # response = self.execute(sql, 'post')
        except Exception as e:
            print(e)
        return response

    def call(self, procedure, cmd='get'):
        response = {}
        try:
            sql = f'CALL {procedure}()'
            response = self.execute(sql, cmd=cmd)
        except Exception as e:
            print(e)
        return response
