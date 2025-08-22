import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Criar aplicação Flask
app = Flask(__name__)

# ================================
# CONFIGURAÇÕES DO BRAINCHILD
# ================================

# Chave secreta para sessões e formulários
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'brainchild-dev-secret-2024'

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///brainchild.db'

# Fix para PostgreSQL no Render (substitui postgres:// por postgresql://)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://",
                                                                                          "postgresql://", 1)

# Outras configurações
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo para upload

# ================================
# INICIALIZAR EXTENSÕES
# ================================

# Banco de dados
db = SQLAlchemy(app)

# Migrações do banco
migrate = Migrate(app, db)

# Sistema de login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

# ================================
# IMPORTAR MODELOS DO BANCO
# ================================

from models.user import User, QuizResult
from models.quiz import Quiz
from models.question import Question


# Função necessária para o Flask-Login carregar usuários
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================================
# IMPORTAR E REGISTRAR ROTAS
# ================================

from routes.auth import auth
from routes.dashboard import dashboard
from routes.quiz import quiz
from routes.user import user

# Registrar blueprints (grupos de rotas)
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(dashboard, url_prefix='/dashboard')
app.register_blueprint(quiz, url_prefix='/quiz')
app.register_blueprint(user, url_prefix='/user')


# ================================
# ROTAS PRINCIPAIS
# ================================

@app.route('/')
def index():
    """Página inicial - redireciona conforme login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))


# ================================
# FUNÇÕES AUXILIARES PARA TEMPLATES
# ================================

@app.context_processor
def inject_global_vars():
    """Disponibiliza variáveis em todos os templates"""
    return {
        'current_user': current_user,
        'User': User,
        'app_name': 'Brainchild'
    }


# ================================
# INICIALIZAÇÃO DO BANCO E DADOS
# ================================

def create_admin_user():
    """Cria usuário administrador padrão se não existir"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin_user = User(
            username='admin',
            email='admin@brainchild.com',
            password_hash=generate_password_hash('admin123'),
            first_name='Administrador',
            last_name='Brainchild',
            phone='',
            user_type='admin',
            is_approved=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Usuário administrador criado!")
        print("📧 Email: admin@brainchild.com")
        print("🔑 Senha: admin123")
        print("⚠️  IMPORTANTE: Altere esta senha após o primeiro login!")


# ================================
# INICIALIZAÇÃO - COMPATÍVEL COM FLASK 3.0+
# ================================

with app.app_context():
    """Executado quando o app é inicializado"""
    # Criar todas as tabelas do banco
    db.create_all()
    
    # Criar usuário admin padrão
    create_admin_user()
    
    print("🚀 Brainchild inicializado com sucesso!")


# ================================
# PREPARAR DIRETÓRIOS NECESSÁRIOS
# ================================

# Criar diretório de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ================================
# EXECUTAR APLICAÇÃO
# ================================

if __name__ == '__main__':
    # Determinar se está em desenvolvimento ou produção
    debug_mode = os.environ.get('FLASK_ENV') == 'development'

    print("🧠 Iniciando Brainchild...")
    print(f"🔧 Modo: {'Desenvolvimento' if debug_mode else 'Produção'}")
    print(f"🗄️  Banco: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Rodar aplicação
    app.run(
        debug=debug_mode,
        host='0.0.0.0',  # Permite acesso externo
        port=int(os.environ.get('PORT', 5000))  # Porta flexível para deploy
    )
