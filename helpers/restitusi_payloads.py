import json
import os
from copy import deepcopy
from utils.generators import today
from helpers.restitusi_calculator import calculate_restitusi_expected
from datetime import datetime, timedelta

def load_json_template(filename):
    filepath = os.path.join(os.path.dirname(__file__), '..', 'payloads', filename)
    with open(filepath, 'r') as f:
        return json.load(f)

def build_restitusi_submit_payload(nomor_loan, plus_days, premi, tenor, transaction_type="REFUND", overcharge=False, undercharge=False):
    payload = load_json_template('submit_restitusi.json')
    payload["nomor_loan"] = nomor_loan
    payload["transaction_type"] = transaction_type
    t_mulai = datetime.now()
    t_restitusi = t_mulai + timedelta(days=plus_days)
    payload["tanggal_restitusi"] = t_restitusi.strftime("%Y-%m-%d")
    
    # Calculate value
    expected_value = calculate_restitusi_expected(t_mulai.strftime("%Y-%m-%d"), t_restitusi.strftime("%Y-%m-%d"), tenor, premi)
    if overcharge:
        expected_value = float(premi) + 500000.0
    elif undercharge:
        # Kurangi nilai agar menjadi < kalkulasi Askrindo (e.g. kurangi 50000 atau kurangi 1 jika nilainya kecil)
        expected_value = float(expected_value) - 50000.0
        if expected_value < 0:
            expected_value = 0.0
            
    payload["nilai_pengajuan"] = round(expected_value, 2)
    
    return payload

def build_restitusi_confirmation_payload(nomor_loan, status, nilai=None, catatan=None):
    if status == "DISETUJUI":
        payload = load_json_template('confirmation.json')
        payload["nomor_loan"] = nomor_loan
        payload["status"] = status
        if nilai is not None:
            payload["nilai"] = round(nilai, 2)
        if catatan is not None:
            payload["catatan"] = catatan
    else:
        payload = load_json_template('sanggahan.json')
        payload["nomor_loan"] = nomor_loan
        payload["status"] = status
        if nilai is not None:
            payload["nilai"] = round(nilai, 2)
        if catatan is not None:
            payload["catatan"] = catatan
    return payload

def build_restitusi_dispute_payload(nomor_loan, nilai_pengajuan, nilai_sebelumnya):
    payload = load_json_template('dispute.json')
    payload["nomor_loan"] = nomor_loan
    payload["nilai_pengajuan"] = round(nilai_pengajuan, 2)
    payload["nilai_sebelumnya"] = round(nilai_sebelumnya, 2)
    return payload
