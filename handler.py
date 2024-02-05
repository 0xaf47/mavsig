import subprocess
import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from mavftp_lib import FileTransfer as mavftp
import argparse
import hashlib
import os
def sign(input_file="out.bin", output_file="output.sig"):
    sign_command = ['pkcs11-tool', '--module', 'librtpkcs11ecp.so', '--login', '--pin', '12345678', '--mechanism', 'SHA256-RSA-PKCS', '--sign', '--input-file', input_file, '--output-file', output_file, '--id', '0100']
    try:
        subprocess.run(command, check=True)
        print("Command executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
def verify_signature(input_file, signature_file, public_key_file):
    # Загружаем открытый ключ из файла
    with open(public_key_file, 'rb') as key_file:
        public_key = load_pem_public_key(key_file.read())

    # Читаем данные из файла
    with open(input_file, 'rb') as file:
        data = file.read()

    # Читаем подпись из файла
    with open(signature_file, 'rb') as file:
        signature = file.read()

    try:
        # Проверяем подпись
        public_key.verify(
            signature,
            data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except:
        return False


def get_file_hash(filename, algorithm='sha256', block_size=65536):
    # Открываем файл в бинарном режиме
    with open(filename, 'rb') as f:
        # Создаем объект хэша указанного алгоритма
        hash_obj = hashlib.new(algorithm)

        # Читаем файл по блокам и обновляем хэш
        while True:
            data = f.read(block_size)
            if not data:
                break
            hash_obj.update(data)

    # Получаем хэш в виде строки
    hash_str = hash_obj.hexdigest()

    return str(hash_str)

def gen_key(filename="key.txt"):
    # Генерируем 64 случайных байта
    key = os.urandom(64)
    #key = bytes([0x04] * 64)
    # Записываем ключ в файл
    with open(filename, 'wb') as f:
        f.write(key)


def gsc_handler(connection_string, baud_rate):
    key_hash = ""
    sig_hash = ""


    while True:
        gen_key()
        mav = mavftp(connection_string, baud_rate)
        
        print("Connected")
        mav.send("key.txt")

        time.sleep(5)
        print("Current keyfile is " + get_file_hash("key.txt"))
        #mav.message((get_file_hash("key.txt")).encode())
        mav.message(get_file_hash("key.txt"))
        print("hello message sent")

        mav.close()
        time.sleep(10)
        '''
        print("Waiting for signature")
        sig_hash = mav.wait()
        print(bytes(key_hash.encode('utf-8')))
        print("Getting file...")

        mav.get("output.sig")
        time.sleep(1)
        mav.close()
        if not (sig_hash[4:10] == get_file_hash("out.bin")[:6]):
            print(sig_hash[4:10], get_file_hash("out.bin")[:6])
            print("Error downloading sigfile, reconnect...")
            continue
        print("New sigfile received, signing... ")
        '''

        mav = mavftp(connection_string, baud_rate)
        print("Connected")
        print("Getting file...")
        mav.get("output.sig")
        time.sleep(2)
        mav.close()
        ver_res = verify_signature("key.txt", "out.bin", "public_key.pem")
        if ver_res == True:
            print ("Key successfully verified")
        else:
            print("Key check failed")
        input()



def drone_handler(connection_string, baud_rate):
    key_hash = ""
    sig_hash = ""
    

    while True:
        mav = mavftp(connection_string, baud_rate)
        print("Connected")
        key_hash = mav.wait()
        print(bytes(key_hash.encode('utf-8')))
        print("Getting file...")

        mav.get("key.txt")
        time.sleep(1)
        mav.close()
        if not (key_hash[4:10] == get_file_hash("out.bin")[:6]):
            print(key_hash[4:10], get_file_hash("out.bin")[:6])
            print("Error downloading keyfile, reconnect...")
            continue
        print("New keyfile received, signing... ")
        sign()
        time.sleep(1.5)
        print("Singed")

        mav = mavftp(connection_string, baud_rate)
        mav.send("output.sig")
        time.sleep(1)
        mav.close()


     

# Создаем объект парсера
parser = argparse.ArgumentParser(description='Mavsig v1.0')

# Добавляем аргументы
parser.add_argument('--mode', type=str, help='Режим работы')
parser.add_argument('--baudrate', type=int, help='Скорость передачи данных')
parser.add_argument('--port', type=str, help='Порт подключения')

# Получаем значения аргументов
args = parser.parse_args()

# Используем значения аргументов
print(args.mode)
print(args.baudrate)
print(args.port)
print(get_file_hash("out.bin"))
if args.mode == "gcs":
    print("Running in gcs mode")
    gsc_handler(args.port, args.baudrate)

if args.mode == "drone":
    print("Running in drone mode")
    drone_handler(args.port, args.baudrate)

