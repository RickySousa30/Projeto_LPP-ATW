import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Category, Event
from datetime import datetime
from functools import wraps

app = Flask(__name__)
# Configuração base: usar SQLite para desenvolvimento inicial, fácil migrar para MySQL depois
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ispgaya.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ispgaya_secret_key_cultural_lab_2025' # Secret key for session/flash
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Garantir que a pasta de uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Decorator para login obrigatório no backoffice
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicie sessão para aceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# ROTAS DO FRONTOFFICE (PÚBLICO)
# ==========================================

@app.route('/')
def index():
    # Destaques de eventos futuros
    upcoming_events = Event.query.filter(Event.date >= datetime.utcnow()).order_by(Event.date.asc()).limit(3).all()
    return render_template('index.html', events=upcoming_events)

@app.route('/clube_leitura')
def clube_leitura():
    events = Event.query.filter_by(type='leitura').order_by(Event.date.asc()).all()
    return render_template('clube_leitura.html', events=events)

@app.route('/clube_teatro')
def clube_teatro():
    events = Event.query.filter_by(type='teatro').order_by(Event.date.asc()).all()
    # Separar ensaios/espetáculos vs notícias se necessário
    return render_template('clube_teatro.html', events=events)

@app.route('/programacao_externa')
def programacao_externa():
    # Lógica de Filtros
    city = request.args.get('cidade')
    category_id = request.args.get('categoria')
    
    query = Event.query.filter_by(type='externa')
    if city:
        query = query.filter(Event.city.ilike(f'%{city}%'))
    if category_id:
        query = query.filter_by(category_id=category_id)
        
    events = query.order_by(Event.date.asc()).all()
    categories = Category.query.all()
    # Obter cidades únicas para o filtro
    cities = db.session.query(Event.city).filter(Event.city.isnot(None), Event.type=='externa').distinct().all()
    cities = [c[0] for c in cities if c[0]]
    
    return render_template('programacao_externa.html', events=events, categories=categories, cities=cities)

@app.route('/evento/<int:id>')
def evento_detalhe(id):
    event = Event.query.get_or_404(id)
    return render_template('evento_detalhe.html', event=event)


# ==========================================
# ROTAS DE AUTENTICAÇÃO
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login efetuado com sucesso!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('index'))


# ==========================================
# ROTAS DO BACKOFFICE (ADMINISTRAÇÃO)
# ==========================================

@app.route('/admin')
@login_required
def admin_dashboard():
    events_count = Event.query.count()
    categories_count = Category.query.count()
    return render_template('admin/dashboard.html', events_count=events_count, categories_count=categories_count)

# --- Gestão de Categorias ---

@app.route('/admin/categorias')
@login_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categorias/nova', methods=['GET', 'POST'])
@login_required
def admin_category_add():
    if request.method == 'POST':
        name = request.form['name']
        if name:
            cat = Category(name=name)
            db.session.add(cat)
            db.session.commit()
            flash('Categoria adicionada!', 'success')
            return redirect(url_for('admin_categories'))
    return render_template('admin/category_form.html')

@app.route('/admin/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_category_edit(id):
    cat = Category.query.get_or_404(id)
    if request.method == 'POST':
        cat.name = request.form['name']
        db.session.commit()
        flash('Categoria atualizada!', 'success')
        return redirect(url_for('admin_categories'))
    return render_template('admin/category_form.html', category=cat)

@app.route('/admin/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
def admin_category_delete(id):
    cat = Category.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria eliminada!', 'success')
    return redirect(url_for('admin_categories'))

# --- Gestão de Eventos ---

@app.route('/admin/eventos')
@login_required
def admin_events():
    events = Event.query.order_by(Event.date.desc()).all()
    return render_template('admin/events.html', events=events)

@app.route('/admin/eventos/novo', methods=['GET', 'POST'])
@login_required
def admin_event_add():
    categories = Category.query.all()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        date_str = request.form['date']
        location = request.form.get('location', '')
        city = request.form.get('city', '')
        type_ = request.form['type']
        category_id = request.form.get('category_id')
        if not category_id: category_id = None
        
        # Parse date
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            date_obj = datetime.now() # Fallback
            
        event = Event(title=title, description=description, date=date_obj,
                      location=location, city=city, type=type_, category_id=category_id)
        db.session.add(event)
        db.session.commit()
        flash('Evento adicionado!', 'success')
        return redirect(url_for('admin_events'))
        
    return render_template('admin/event_form.html', categories=categories)

@app.route('/admin/eventos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_event_edit(id):
    event = Event.query.get_or_404(id)
    categories = Category.query.all()
    if request.method == 'POST':
        event.title = request.form['title']
        event.description = request.form.get('description', '')
        date_str = request.form['date']
        event.location = request.form.get('location', '')
        event.city = request.form.get('city', '')
        event.type = request.form['type']
        
        cat_id = request.form.get('category_id')
        event.category_id = int(cat_id) if cat_id else None
        
        try:
            event.date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass # keep old date
            
        db.session.commit()
        flash('Evento atualizado!', 'success')
        return redirect(url_for('admin_events'))
        
    return render_template('admin/event_form.html', event=event, categories=categories)

@app.route('/admin/eventos/eliminar/<int:id>', methods=['POST'])
@login_required
def admin_event_delete(id):
    event = Event.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    flash('Evento eliminado!', 'success')
    return redirect(url_for('admin_events'))

# ==========================================
# INICIALIZAÇÃO DA BASE DE DADOS E ADMIN
# ==========================================
def setup_database():
    with app.app_context():
        db.create_all()
        # Verificar se existe user admin
        if User.query.filter_by(username='admin').first() is None:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123') # Default password
            db.session.add(admin)
            
            # Adicionar categorias iniciais
            for cat_name in ['Teatro', 'Música', 'Literatura', 'Exposições']:
                if Category.query.filter_by(name=cat_name).first() is None:
                    db.session.add(Category(name=cat_name))
                    
            db.session.commit()
            print("Base de dados inicializada e utilizador 'admin' criado (password: admin123).")

if __name__ == '__main__':
    setup_database()
    app.run(debug=True, port=5000)
