import os
import sys
import argparse
from dotenv import load_dotenv

# Append project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load generic UI helpers and DB clients
from db.client import DatabaseClient
from db.acs_client import execute_acs_query

def main():
    parser = argparse.ArgumentParser(description="Unified Database Query Checker")
    parser.add_argument("--env", choices=["staging", "uat"], default="uat", help="Environment to run against (default: uat)")
    
    subparsers = parser.add_subparsers(dest="command", help="Query Commands")
    
    # Check ACS Policy
    acs_parser = subparsers.add_parser("acs", help="Check Policy in ACS (MSSQL)")
    acs_parser.add_argument("--polis", required=True, help="Nomor Polis to search in ACS")
    
    # Check Internal Policy (t_sertifikat, t_sertifikat_dtl)
    cert_parser = subparsers.add_parser("cert", help="Check Policy/Sertifikat in Internal DB (PostgreSQL)")
    cert_parser.add_argument("--polis", required=True, help="Nomor Polis/Sertifikat to search")
    
    # Check Transaction Status
    status_parser = subparsers.add_parser("status", help="Check Transaction Status (t_sp2k_submission)")
    status_parser.add_argument("--trx", required=True, help="Nomor Transaksi to search")
    
    # Check Pembayaran
    pay_parser = subparsers.add_parser("pay", help="Check Pembayaran for Transaction")
    pay_parser.add_argument("--trx", required=True, help="Nomor Transaksi to search")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return

    # Set environment variables so the clients connect to the right DB
    if args.env == "uat":
        load_dotenv(".env.uat")
        os.environ["TEST_ENV"] = "uat"
    else:
        load_dotenv(".env.staging")
        os.environ["TEST_ENV"] = "staging"

    # Execute based on command
    if args.command == "acs":
        print(f"[{args.env.upper()}] Checking ACS DB for Polis: {args.polis}")
        query = f"SELECT TOP 10 NoPolis, NoPolisAsli FROM tb_Polis WHERE NoPolis LIKE '%{args.polis}%';"
        try:
            results = execute_acs_query(query)
            print(f"Found {len(results)} rows:")
            for row in results:
                print(row)
        except Exception as e:
            print(f"Error querying ACS: {e}")
            
    elif args.command == "cert":
        print(f"[{args.env.upper()}] Checking Internal DB for Sertifikat: {args.polis}")
        db = DatabaseClient()
        query = "SELECT no_sertifikat, status_epolis FROM t_sertifikat WHERE no_sertifikat LIKE %s;"
        query_dtl = "SELECT no_sertifikat, no_sertifikat_prev, creation_type FROM t_sertifikat_dtl WHERE no_sertifikat LIKE %s;"
        
        print("\n--- t_sertifikat ---")
        for row in db.execute_query(query, (f"%{args.polis}%",)):
            print(row)
            
        print("\n--- t_sertifikat_dtl ---")
        for row in db.execute_query(query_dtl, (f"%{args.polis}%",)):
            print(row)

    elif args.command == "status":
        print(f"[{args.env.upper()}] Checking Transaction Status for: {args.trx}")
        db = DatabaseClient()
        query = "SELECT status_akseptasi, nomor_transaksi FROM t_sp2k_submission WHERE nomor_transaksi = %s;"
        for row in db.execute_query(query, (args.trx,)):
            print(row)
            
    elif args.command == "pay":
        print(f"[{args.env.upper()}] Checking Payment for Transaction: {args.trx}")
        db = DatabaseClient()
        query = """
            SELECT a.id_pembayaran, a.nominal_pengajuan_mitra, a.nominal_disetujui, a.no_jurnal_bk, a.tanggal_bayar 
            FROM t_pembayaran a 
            JOIN t_sp2k_submission b ON a.id_sp2k_submission = b.id_sp2k_submission 
            WHERE b.nomor_transaksi = %s;
        """
        results = db.execute_query(query, (args.trx,))
        print(f"Found {len(results)} payment records:")
        for row in results:
            print(row)

if __name__ == "__main__":
    main()
