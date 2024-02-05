import time
from pymavlink import mavutil
import threading
import random
connection_string = '/dev/ttyUSB0' # заменить на соответствующий порт
baud_rate = 57600 # скорость передачи данных

class FileTransfer:

    state = 0

    def __init__(self, connection_string, baud_rate):
        self.mav = mavutil.mavlink_connection(connection_string, baud=baud_rate)
        self.mav.robust_parsing = True
        self.mav.wait_heartbeat()

    def send(self, file_path):
        while True:
            if self.state != 0:
                time.sleep(1)
            else:
                break
        self.state = 1
        file_bytes = []
        with open(file_path, "rb") as file:
            byte = file.read(1)
            while byte:
                file_bytes.append(ord(byte))
                byte = file.read(1)
        parts = gen_payload(3,"put", file_path, file_bytes)
        for part in parts:
            self.mav.mav.file_transfer_protocol_send(0, 1, 1, part)
            time.sleep(0.1)
            #print(part)
        ACK = gen_payload(3,"ACK")
        ACK[0] = parts[-1][0]+1
        self.mav.mav.file_transfer_protocol_send(0, 1, 1, ACK)
        self.state = 0
        print("Sent")

    def get(self, file_path,):
        while True:
            if self.state != 0:
                time.sleep(1)
            else:
                break
        self.state = 1
        parts = gen_payload(3, "get", file_path)
        mav = self.mav
        self.process_messages(parts, mav)
        #receive_thread = threading.Thread(target=self.process_messages, args=(parts,mav,))
        #receive_thread.start()

    def process_messages(self, parts, mav):
        data = []
        for part in parts:
            mav.mav.file_transfer_protocol_send(0, 1, 1, part)
            time.sleep(0.1)
        print("Sent")
        while True:
            try:
                # чтение пакета
                msg = mav.recv_match()
                if not msg:
                    continue
                # обработка пакета
                if msg.get_type() == 'FILE_TRANSFER_PROTOCOL':
                    #print('FTP received')
                    #print(msg.payload)
                    #print(msg.payload[6])
                    if msg.payload[5] == 15 and msg.payload[3] != 129:
                        data.append(msg.payload)
                    if msg.payload[3] == 129:
                        write_file(extract_data(data))
                        ACK = gen_payload(3,"ACK")
                        ACK[0] = msg.payload[0]+1
                        break
            except KeyboardInterrupt:
                        print('Exiting')
                        break
            time.sleep(0.1)
        mav.mav.file_transfer_protocol_send(0, 1, 1, ACK)
        self.state = 0
        return(0)
    def close(self):
        while True:
            if self.state != 1:
                print("Closing...")
                self.mav.close()
                break
            else:
                time.sleep(1)

    def message(self, text="hash"+ 64*"0"):
        self.mav.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_INFO, text.encode('ISO-8859-1'))

    def wait(self):
        while True:
            msg = self.mav.recv_match()
            if not msg:
                continue
                # обработка пакета
            #print(msg)
            
            if msg.get_type() == 'STATUSTEXT':
                payload = msg.get_payload()
                if payload != None and (len(payload.decode('ISO-8859-1')) > 50):
                    print((payload.decode('ISO-8859-1')).replace("ý", ""))
                    return((payload.decode('ISO-8859-1')).replace("ý", ""))

            time.sleep(0.1)

def extract_data(data):
    clear_data = []
    for sublist in data:
        for i in range(12, (len(sublist)-1)):
            if sublist[i]==0 and sublist[i+1]==0:
                break
            clear_data.append(sublist[i])
    return clear_data

def write_file(clear_data):
    with open('out.bin', 'wb') as file:
        # Записываем байты в файл
        file.write(bytes(clear_data))

def gen_payload(session, op, filename=None, file=None):
    if file == None:
        file = []
    if op == "get":
        payload = [0] * 251
        data = list(filename.encode())
        start_index=12
        end_index = start_index + len(data)
        payload[start_index:end_index]=data
        payload[0] = 1
        payload[2] = session
        payload[3] = 4
        payload[4] = len(data)
        payload2 = [0] * 251
        payload2[0] = payload[0]+1
        payload2[2] = 3
        payload2[3] = 15
        payload2[4] = 80
        return(payload,payload2)
    if op == "put" and file != None:
        file_payload = []
        block_len = 80
        file_len = len(file)
        if file_len >= block_len:
            blocks = file_len//block_len+1
        else:
            blocks = 1
        payload = [0] * 251
        data = list(filename.encode())
        start_index=12
        end_index = start_index + len(data)
        payload[start_index:end_index]=data
        payload[0] = 1
        payload[2] = session
        payload[3] = 6
        payload[4] = len(data)
        file_payload.append(payload)
        for block in range(blocks):
            payload2 = [0] * 251
            payload2[0] = 2+block
            payload2[2] = session
            payload2[3] = 7
            start_index=12
            offset = block*block_len
            payload2[8] = offset & 0xFF  # Младший байт
            payload2[9] = (offset >> 8) & 0xFF
            if block != blocks-1:
                end_index = start_index + block_len
                payload2[4] = block_len
                payload2[start_index:end_index] = file[(block)*block_len:(block+1)*block_len]
            if block == blocks-1:
                end_index = start_index + file_len%block_len
                payload2[4] = file_len%block_len
                #print("end index is " + str(end_index))
                payload2[start_index:end_index] = file[(block)*block_len:file_len]
            file_payload.append(payload2)
        file_payload = tuple(file_payload)
        return(file_payload)
    if op == "ACK":
        payload = [0] * 251
        payload[2:3] = [session,1]
        return payload



