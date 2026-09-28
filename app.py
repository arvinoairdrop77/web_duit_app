from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from werkzeug.security import check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'wongikijanepekok'

DB_CONFIG = {
    'dbname': 'db_duit_app',
    'user': 'arvino',
    'password': 'gatya123',
    'host': '127.0.0.1',
    'port': '5432'
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        tanggal = request.form['tanggal']
        keterangan = request.form['keterangan']
        jenis = request.form['jenis']
        id_kategori = request.form['id_kategori']
        nominal = request.form['nominal']

        cur.execute("""
            INSERT INTO transaksi (tanggal, keterangan, jenis, id_kategori, nominal, id_user)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tanggal, keterangan, jenis, id_kategori, nominal, user_id))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    today = datetime.now()
    bulan_selected = request.args.get('bulan', type=int, default=today.month)
    tahun_selected = request.args.get('tahun', type=int, default=today.year)

    # 1. Ringkasan Kartu
    cur.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN jenis = 'Pemasukan' THEN nominal ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN jenis = 'Pengeluaran' THEN nominal ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN jenis = 'Pemasukan' THEN nominal ELSE -nominal END), 0)
        FROM transaksi
        WHERE id_user = %s 
          AND EXTRACT(MONTH FROM tanggal) = %s 
          AND EXTRACT(YEAR FROM tanggal) = %s;
    """, (user_id, bulan_selected, tahun_selected))
    summary = cur.fetchone()

    # 2. Daftar Kategori
    cur.execute("SELECT id_kategori, nama_kategori, jenis FROM kategori ORDER BY nama_kategori ASC")
    kategori_list = cur.fetchall()

    # 3. Riwayat Transaksi
    cur.execute("""
        SELECT t.id_transaksi, t.tanggal, t.keterangan, k.nama_kategori, t.jenis, t.nominal
        FROM transaksi t
        LEFT JOIN kategori k ON t.id_kategori = k.id_kategori
        WHERE t.id_user = %s
          AND EXTRACT(MONTH FROM t.tanggal) = %s
          AND EXTRACT(YEAR FROM t.tanggal) = %s
        ORDER BY t.tanggal DESC, t.id_transaksi DESC
    """, (user_id, bulan_selected, tahun_selected))
    transaksi_list = cur.fetchall()

    # 4. Data untuk Chart.js (Total Pengeluaran per Kategori)
    cur.execute("""
        SELECT k.nama_kategori, COALESCE(SUM(t.nominal), 0)
        FROM transaksi t
        JOIN kategori k ON t.id_kategori = k.id_kategori
        WHERE t.id_user = %s
          AND t.jenis = 'Pengeluaran'
          AND EXTRACT(MONTH FROM t.tanggal) = %s
          AND EXTRACT(YEAR FROM t.tanggal) = %s
        GROUP BY k.nama_kategori
        ORDER BY SUM(t.nominal) DESC
    """, (user_id, bulan_selected, tahun_selected))
    chart_raw = cur.fetchall()

    cur.close()
    conn.close()

    chart_labels = [row[0] for row in chart_raw]
    chart_values = [float(row[1]) for row in chart_raw]

    nama_bulan = [
        (1, 'Januari'), (2, 'Februari'), (3, 'Maret'), (4, 'April'),
        (5, 'Mei'), (6, 'Juni'), (7, 'Juli'), (8, 'Agustus'),
        (9, 'September'), (10, 'Oktober'), (11, 'November'), (12, 'Desember')
    ]
    daftar_tahun = list(range(today.year - 2, today.year + 2))

    return render_template('index.html',
                           summary=summary,
                           kategori_list=kategori_list,
                           transaksi_list=transaksi_list,
                           bulan_selected=bulan_selected,
                           tahun_selected=tahun_selected,
                           nama_bulan=nama_bulan,
                           daftar_tahun=daftar_tahun,
                           chart_labels=chart_labels,
                           chart_values=chart_values)

@app.route('/hapus/<int:id_transaksi>', methods=['POST', 'GET'])
def hapus_transaksi(id_transaksi):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM transaksi WHERE id_transaksi = %s AND id_user = %s", (id_transaksi, user_id))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
