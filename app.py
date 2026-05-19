import sqlite3
import json
import csv
import io
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash

app = Flask(__name__)
app.secret_key = 'rfb-spreuken-2026'
DB = 'spreuken.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS categorie (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                naam TEXT NOT NULL UNIQUE,
                beschrijving TEXT
            );
            CREATE TABLE IF NOT EXISTS spreuk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tekst_nl TEXT NOT NULL,
                tekst_en TEXT,
                auteur TEXT,
                bron TEXT,
                origine TEXT,
                taal_origineel TEXT DEFAULT 'nl',
                categorie_id INTEGER REFERENCES categorie(id),
                datum_toegevoegd DATE DEFAULT (date('now')),
                notitie TEXT,
                favoriet INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                naam TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS spreuk_tag (
                spreuk_id INTEGER REFERENCES spreuk(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
                PRIMARY KEY (spreuk_id, tag_id)
            );
        ''')
        # Seed categories if empty
        if not db.execute('SELECT 1 FROM categorie LIMIT 1').fetchone():
            cats = [
                ('Filosofie', 'Wijsheid en levensbeschouwing'),
                ('Motivatie', 'Inspirerende uitspraken'),
                ('Humor', 'Grappige en geestige spreuken'),
                ('Liefde', 'Over liefde en relaties'),
                ('Leiderschap', 'Over leiding geven'),
                ('Natuur', 'Over de natuur en het leven'),
            ]
            db.executemany('INSERT INTO categorie (naam, beschrijving) VALUES (?,?)', cats)

@app.route('/')
def index():
    db = get_db()
    q = request.args.get('q', '')
    cat_id = request.args.get('cat', '')
    only_fav = request.args.get('fav', '')
    taal = request.args.get('taal', '')

    query = '''SELECT s.*, c.naam as categorie_naam
               FROM spreuk s LEFT JOIN categorie c ON s.categorie_id = c.id
               WHERE 1=1'''
    params = []
    if q:
        query += ' AND (s.tekst_nl LIKE ? OR s.tekst_en LIKE ? OR s.auteur LIKE ?)'
        params += [f'%{q}%', f'%{q}%', f'%{q}%']
    if cat_id:
        query += ' AND s.categorie_id = ?'
        params.append(cat_id)
    if only_fav:
        query += ' AND s.favoriet = 1'
    if taal:
        query += ' AND s.taal_origineel = ?'
        params.append(taal)
    query += ' ORDER BY s.datum_toegevoegd DESC, s.id DESC'

    spreuken = db.execute(query, params).fetchall()
    categorieen = db.execute('SELECT * FROM categorie ORDER BY naam').fetchall()
    totaal = db.execute('SELECT COUNT(*) FROM spreuk').fetchone()[0]
    favorieten = db.execute('SELECT COUNT(*) FROM spreuk WHERE favoriet=1').fetchone()[0]
    dagelijks = db.execute(
        'SELECT s.*, c.naam as categorie_naam FROM spreuk s LEFT JOIN categorie c ON s.categorie_id=c.id ORDER BY RANDOM() LIMIT 1'
    ).fetchone()
    return render_template('index.html',
        spreuken=spreuken, categorieen=categorieen, totaal=totaal,
        favorieten=favorieten, dagelijks=dagelijks,
        q=q, cat_id=cat_id, only_fav=only_fav, taal=taal)

@app.route('/spreuk/nieuw', methods=['GET', 'POST'])
def nieuw():
    db = get_db()
    if request.method == 'POST':
        tags_raw = request.form.get('tags', '')
        tag_namen = [t.strip() for t in tags_raw.split(',') if t.strip()]
        cur = db.execute('''INSERT INTO spreuk
            (tekst_nl, tekst_en, auteur, bron, origine, taal_origineel,
             categorie_id, datum_toegevoegd, notitie, favoriet)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', (
            request.form['tekst_nl'],
            request.form.get('tekst_en') or None,
            request.form.get('auteur') or None,
            request.form.get('bron') or None,
            request.form.get('origine') or None,
            request.form.get('taal_origineel', 'nl'),
            request.form.get('categorie_id') or None,
            request.form.get('datum_toegevoegd') or str(date.today()),
            request.form.get('notitie') or None,
            1 if request.form.get('favoriet') else 0,
        ))
        spreuk_id = cur.lastrowid
        for naam in tag_namen:
            db.execute('INSERT OR IGNORE INTO tag (naam) VALUES (?)', (naam,))
            tag = db.execute('SELECT id FROM tag WHERE naam=?', (naam,)).fetchone()
            db.execute('INSERT OR IGNORE INTO spreuk_tag VALUES (?,?)', (spreuk_id, tag['id']))
        db.commit()
        flash('Spreuk toegevoegd!', 'success')
        return redirect(url_for('index'))
    categorieen = db.execute('SELECT * FROM categorie ORDER BY naam').fetchall()
    return render_template('form.html', spreuk=None, categorieen=categorieen, actie='Toevoegen')

@app.route('/spreuk/<int:sid>/bewerk', methods=['GET', 'POST'])
def bewerk(sid):
    db = get_db()
    spreuk = db.execute('SELECT * FROM spreuk WHERE id=?', (sid,)).fetchone()
    if not spreuk:
        return redirect(url_for('index'))
    tags = db.execute(
        'SELECT t.naam FROM tag t JOIN spreuk_tag st ON t.id=st.tag_id WHERE st.spreuk_id=?', (sid,)
    ).fetchall()
    tags_str = ', '.join(t['naam'] for t in tags)
    if request.method == 'POST':
        db.execute('''UPDATE spreuk SET
            tekst_nl=?, tekst_en=?, auteur=?, bron=?, origine=?,
            taal_origineel=?, categorie_id=?, datum_toegevoegd=?, notitie=?, favoriet=?
            WHERE id=?''', (
            request.form['tekst_nl'],
            request.form.get('tekst_en') or None,
            request.form.get('auteur') or None,
            request.form.get('bron') or None,
            request.form.get('origine') or None,
            request.form.get('taal_origineel', 'nl'),
            request.form.get('categorie_id') or None,
            request.form.get('datum_toegevoegd') or str(date.today()),
            request.form.get('notitie') or None,
            1 if request.form.get('favoriet') else 0,
            sid,
        ))
        db.execute('DELETE FROM spreuk_tag WHERE spreuk_id=?', (sid,))
        tags_raw = request.form.get('tags', '')
        for naam in [t.strip() for t in tags_raw.split(',') if t.strip()]:
            db.execute('INSERT OR IGNORE INTO tag (naam) VALUES (?)', (naam,))
            tag = db.execute('SELECT id FROM tag WHERE naam=?', (naam,)).fetchone()
            db.execute('INSERT OR IGNORE INTO spreuk_tag VALUES (?,?)', (sid, tag['id']))
        db.commit()
        flash('Spreuk bijgewerkt!', 'success')
        return redirect(url_for('index'))
    categorieen = db.execute('SELECT * FROM categorie ORDER BY naam').fetchall()
    return render_template('form.html', spreuk=spreuk, categorieen=categorieen,
                           actie='Bewerken', tags_str=tags_str)

@app.route('/spreuk/<int:sid>/verwijder', methods=['POST'])
def verwijder(sid):
    db = get_db()
    db.execute('DELETE FROM spreuk WHERE id=?', (sid,))
    db.commit()
    flash('Spreuk verwijderd.', 'info')
    return redirect(url_for('index'))

@app.route('/spreuk/<int:sid>/favoriet', methods=['POST'])
def toggle_favoriet(sid):
    db = get_db()
    db.execute('UPDATE spreuk SET favoriet = 1 - favoriet WHERE id=?', (sid,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/categorieen', methods=['GET', 'POST'])
def categorieen():
    db = get_db()
    if request.method == 'POST':
        naam = request.form.get('naam', '').strip()
        beschr = request.form.get('beschrijving', '').strip()
        if naam:
            db.execute('INSERT OR IGNORE INTO categorie (naam, beschrijving) VALUES (?,?)', (naam, beschr))
            db.commit()
            flash(f'Categorie "{naam}" toegevoegd.', 'success')
        return redirect(url_for('categorieen'))
    cats = db.execute(
        '''SELECT c.*, COUNT(s.id) as aantal
           FROM categorie c LEFT JOIN spreuk s ON s.categorie_id = c.id
           GROUP BY c.id ORDER BY c.naam'''
    ).fetchall()
    return render_template('categorieen.html', categorieen=cats)

@app.route('/categorie/<int:cid>/verwijder', methods=['POST'])
def verwijder_categorie(cid):
    db = get_db()
    db.execute('UPDATE spreuk SET categorie_id=NULL WHERE categorie_id=?', (cid,))
    db.execute('DELETE FROM categorie WHERE id=?', (cid,))
    db.commit()
    flash('Categorie verwijderd.', 'info')
    return redirect(url_for('categorieen'))

@app.route('/export/csv')
def export_csv():
    db = get_db()
    rows = db.execute('''SELECT s.tekst_nl, s.tekst_en, s.auteur, s.bron, s.origine,
        s.taal_origineel, c.naam as categorie, s.datum_toegevoegd, s.notitie, s.favoriet
        FROM spreuk s LEFT JOIN categorie c ON s.categorie_id=c.id
        ORDER BY s.datum_toegevoegd DESC''').fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tekst NL','Tekst EN','Auteur','Bron','Origine','Taal origineel',
                     'Categorie','Datum toegevoegd','Notitie','Favoriet'])
    for r in rows:
        writer.writerow(list(r))
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode('utf-8-sig')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='spreuken_export.csv')

@app.route('/export/json')
def export_json():
    db = get_db()
    rows = db.execute('''SELECT s.*, c.naam as categorie_naam
        FROM spreuk s LEFT JOIN categorie c ON s.categorie_id=c.id
        ORDER BY s.datum_toegevoegd DESC''').fetchall()
    data = [dict(r) for r in rows]
    output = json.dumps(data, ensure_ascii=False, indent=2)
    return send_file(io.BytesIO(output.encode('utf-8')),
                     mimetype='application/json',
                     as_attachment=True,
                     download_name='spreuken_export.json')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
