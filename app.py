import os
from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'wongikijanepekok'

DB_CONFIG = {
    'dbname': 'db_duit_app',
    'user': 'arvino',
    'password': 'gatya123',
    'host': '127.0.0.1',
    'port': '5432'
}

DATABASE_URL = os.environ.get('DATABASE_URL')

#def get_db():
#    if DATABASE_URL:
#        return psycopg2.connect(DATABASE_URL, sslmode='require')
#    else:
#        return psycopg2.connect(**DB_CONFIG)

def get_db():
    return psycopg2.connect(**DB_CONFIG)

# --- RUTE HALAMAN LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id_user, username, password FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('index'))
        else:
            error = 'Username atau Password salah!'

    return render_template('login.html', error=error)

# Rute Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# DASHBOARD 
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()


    cur.execute("SELECT * FROM users WHERE id_user = %s", (session['user_id'],))
    user = cur.fetchone()

    # --- PROSES SIMPAN TRANSAKSI BARU (POST) ---
    if request.method == 'POST':
        tanggal = request.form['tanggal']
        keterangan = request.form['keterangan']
        jenis = request.form['jenis']
        id_kategori = request.form['id_kategori']
        nominal = request.form['nominal']

        # Query Simpan Data ke PostgreSQL
        cur.execute("""
            INSERT INTO transaksi (tanggal, keterangan, jenis, id_kategori, nominal)
            VALUES (%s, %s, %s, %s, %s)
        """, (tanggal, keterangan, jenis, id_kategori, nominal))

        conn.commit()
        cur.close()
        conn.close()

        # Refresh halaman setelah simpan
        return redirect(url_for('index'))

    # --- AMBIL DATA UNTUK TAMPILAN (GET) ---
    # 1. Ringkasan Kartu (Pemasukan, Pengeluaran, Sisa Saldo)
    cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN jenis = 'Pemasukan' THEN nominal ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN jenis = 'Pengeluaran' THEN nominal ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN jenis = 'Pemasukan' THEN nominal ELSE -nominal END), 0)
        FROM transaksi;
    """)
    summary = cur.fetchone()

    # 2. Ambil Daftar Kategori untuk Dropdown
    cur.execute("SELECT id_kategori, nama_kategori, jenis FROM kategori ORDER BY nama_kategori ASC")
    kategori_list = cur.fetchall()

    # 3. Ambil Riwayat Transaksi
    cur.execute("""
        SELECT t.id_transaksi, t.tanggal, t.keterangan, k.nama_kategori, t.jenis, t.nominal
        FROM transaksi t
        LEFT JOIN kategori k ON t.id_kategori = k.id_kategori
        ORDER BY t.tanggal DESC, t.id_transaksi DESC
    """)
    transaksi_list = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('index.html', 
                           summary=summary, 
                           kategori_list=kategori_list, 
                           transaksi_list=transaksi_list)

@app.route('/hapus/<int:id_transaksi>', methods=['POST', 'GET'])
def hapus_transaksi(id_transaksi):
    conn = get_db()
    cur = conn.cursor()

    # Eksekusi query hapus berdasarkan id_transaksi
    cur.execute("DELETE FROM transaksi WHERE id_transaksi = %s", (id_transaksi,))

    conn.commit()
    cur.close()
    conn.close()

    # Kembali ke halaman utama setelah data dihapus
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
