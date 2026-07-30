QUERY_CEK_DRAFT_AKSEPTASI = """
SELECT 
    d.id_debitur, d.cif, d.nama_debitur, d.ktp, d.npwp, d.tempat_lahir,
    d.tanggal_lahir, d.jenis_kelamin, d.alamat_debitur, d.kode_pos,
    d.jenis_pekerjaan AS debitur_jenis_pekerjaan,
    d.status_kepegawaian AS debitur_status_kepegawaian,
    d.no_telepon, d.no_handphone, d.nama_ibu_kandung,

    s.id_sp2k_submission, s.nomor_transaksi, s.no_aplikasi, s.kode_bank,
    s.kode_uker, s.request_type, s.status_akseptasi, s.id_product,
    s.id_product_group, s.jenis_covering, s.id_askrindo_branch,
    s.id_broker_agent, s.pks_id,
    
    pr.id AS master_product_id_code, pr.nama_product AS master_product_name,
    pr.jenis_kredit AS master_product_jenis, pr.kode_product_external AS master_product_ext,
    
    a.id_akseptasi_askred, a.jenis_pengajuan, a.tanggal_mulai_covering,
    a.tanggal_akhir_covering, a.nilai_pertanggungan, a.premi, a.rate_premi,
    a.id_valuta, a.kurs_valuta, a.biaya_meterai, a.biaya_admin,
    a.jenis_pekerjaan AS akseptasi_jenis_pekerjaan,
    a.status_kepegawaian AS akseptasi_status_kepegawaian,
    a.mekanisme_penyaluran, a.jangka_waktu, a.nomor_rekening_pinjaman,
    a.nomor_perjanjian_kredit, a.tanggal_perjanjian_kredit, a.outstanding,
    a.kolektibilitas, a.suku_bunga_kredit,
  	
    p.id_payment_account, p.nama_bank, p.nomor_rekening, p.nama_pemilik,

    pay.id_pembayaran, pay.id_sp2k_submission AS pembayaran_id_submission, 
    pay.id_payment_account AS pembayaran_id_account     

FROM t_akseptasi_askred a
JOIN m_debitur d ON a.id_debitur = d.id_debitur
JOIN t_sp2k_submission s ON a.id_submission = s.id_sp2k_submission
LEFT JOIN m_product pr ON s.id_product = pr.id
LEFT JOIN t_pembayaran pay ON s.id_sp2k_submission = pay.id_sp2k_submission
LEFT JOIN m_payment_account p ON pay.id_payment_account = p.id_payment_account
WHERE s.nomor_transaksi = %s;
"""

QUERY_CEK_TERBIT_POLIS = """
SELECT 
    -- 1. Informasi Transaksi & Debitur
    s.nomor_transaksi,
    d.nama_debitur,
    
    -- 2. Kolom dari t_sertifikat
    cert.id_sertifikat,
    cert.no_sertifikat,
    cert.tgl_sertifikat,
    cert.url_download_sertifikat,
    cert.is_polis_sent,
    
    -- 3. Detail Loan & Premi
    a.nomor_perjanjian_kredit AS nomor_loan,
    a.premi

FROM t_sp2k_submission s
JOIN t_akseptasi_askred a 
    ON s.id_sp2k_submission = a.id_submission
JOIN m_debitur d 
    ON a.id_debitur = d.id_debitur
LEFT JOIN t_sertifikat cert 
    ON s.id_sp2k_submission = cert.id_submission
WHERE s.nomor_transaksi = %s;
"""
