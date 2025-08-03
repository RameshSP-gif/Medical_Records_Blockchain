import hashlib
import json
from datetime import datetime

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = {
            'index': 0,
            'timestamp': str(datetime.now()),
            'user_id': 0,
            'file_name': 'genesis',
            'file_path': '',
            'prev_hash': '0',
            'hash': self.calculate_hash(0, '0', str(datetime.now()), 0, '')
        }
        self.chain.append(genesis_block)

    def calculate_hash(self, index, prev_hash, timestamp, user_id, file_path):
        block_string = json.dumps({
            'index': index,
            'prev_hash': prev_hash,
            'timestamp': timestamp,
            'user_id': user_id,
            'file_path': file_path
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def add_block(self, user_id, file_name, file_path, prev_hash):
        block = {
            'index': len(self.chain),
            'timestamp': str(datetime.now()),
            'user_id': user_id,
            'file_name': file_name,
            'file_path': file_path,
            'prev_hash': prev_hash,
            'hash': ''
        }
        block['hash'] = self.calculate_hash(block['index'], block['prev_hash'], block['timestamp'], block['user_id'], block['file_path'])
        self.chain.append(block)
        return block['hash']

    def get_previous_hash(self):
        return self.chain[-1]['hash'] if self.chain else '0'

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            prev_block = self.chain[i-1]
            if current_block['hash'] != self.calculate_hash(
                current_block['index'], current_block['prev_hash'], current_block['timestamp'],
                current_block['user_id'], current_block['file_path']):
                return False
            if current_block['prev_hash'] != prev_block['hash']:
                return False
        return True