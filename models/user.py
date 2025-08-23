"""
Modelo de Usuários - Brainchild
===============================

Define a estrutura dos usuários e suas permissões:
- Administrador: Controle total do sistema
- Moderador: Criar/editar quizzes, aprovar usuários
- Aluno: Jogar quizzes
"""

from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Usar a mesma instância db do app.py - MANTER IMPORTAÇÃO ORIGINAL
try:
    from app import db
except ImportError:
    # Fallback caso haja problema de importação circular
    from flask import current_app
    db = current_app.extensions['sqlalchemy']


class User(UserMixin, db.Model):
    """
    Modelo de usuário do sistema Brainchild
    Herda de UserMixin para compatibilidade com Flask-Login
    """

    __tablename__ = 'users'

    # Campos da tabela
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    user_type = db.Column(db.String(20), nullable=False, default='student')  # admin, moderator, student
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos com outras tabelas - definir apenas se as tabelas existirem
    try:
        quizzes = db.relationship('Quiz', backref='creator', lazy=True, cascade='all, delete-orphan')
        quiz_results = db.relationship('QuizResult', backref='user', lazy=True, cascade='all, delete-orphan')
    except:
        # Se as tabelas Quiz/QuizResult não existirem ainda, ignorar relacionamentos
        pass

    def __init__(self, username, email, password_hash, first_name, last_name, phone='', user_type='student',
                 is_approved=False):
        """Inicializar novo usuário"""
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.user_type = user_type
        self.is_approved = is_approved

    def set_password(self, password):
        """Define nova senha usando hash seguro"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida está correta"""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        """Retorna nome completo do usuário"""
        return f"{self.first_name} {self.last_name}"

    # Propriedades de verificação de tipo de usuário
    @property
    def is_admin(self):
        """Verifica se o usuário é administrador"""
        return self.user_type == 'admin'

    @property
    def is_moderator(self):
        """Verifica se o usuário é moderador"""
        return self.user_type == 'moderator'

    @property
    def is_student(self):
        """Verifica se o usuário é aluno"""
        return self.user_type == 'student'

    # Propriedades de permissões
    @property
    def can_create_quiz(self):
        """Verifica se pode criar quizzes"""
        return self.user_type in ['admin', 'moderator']

    @property
    def can_approve_users(self):
        """Verifica se pode aprovar cadastros pendentes"""
        return self.user_type in ['admin', 'moderator']

    @property
    def can_manage_all_quizzes(self):
        """Verifica se pode gerenciar todos os quizzes (arquivar/excluir)"""
        return self.user_type == 'admin'

    @property
    def can_promote_users(self):
        """Verifica se pode promover/rebaixar usuários"""
        return self.user_type == 'admin'

    @property
    def can_access_admin_panel(self):
        """Verifica se pode acessar painel administrativo"""
        return self.user_type == 'admin'

    def get_user_type_display(self):
        """Retorna o tipo de usuário em português"""
        types = {
            'admin': 'Administrador',
            'moderator': 'Moderador',
            'student': 'Aluno'
        }
        return types.get(self.user_type, 'Desconhecido')

    def get_user_type_color(self):
        """Retorna cor do badge do tipo de usuário"""
        colors = {
            'admin': 'danger',  # Vermelho
            'moderator': 'warning',  # Amarelo
            'student': 'primary'  # Azul
        }
        return colors.get(self.user_type, 'secondary')

    def promote_to_moderator(self):
        """Promove aluno para moderador"""
        if self.user_type == 'student':
            self.user_type = 'moderator'
            return True
        return False

    def demote_to_student(self):
        """Rebaixa moderador para aluno"""
        if self.user_type == 'moderator':
            self.user_type = 'student'
            return True
        return False

    def approve(self):
        """Aprova cadastro pendente"""
        self.is_approved = True

    def reject(self):
        """Rejeita e remove cadastro pendente"""
        # Será implementado na lógica de rotas
        pass

    def get_quiz_stats(self):
        """Retorna estatísticas dos quizzes do usuário"""
        try:
            if self.is_student:
                # Estatísticas para alunos (quizzes jogados)
                quiz_results = getattr(self, 'quiz_results', [])
                total_played = len(quiz_results)
                
                if total_played == 0:
                    return {
                        'quizzes_played': 0,
                        'average_score': 0,
                        'best_score': 0,
                        'total_questions_answered': 0
                    }

                scores = []
                total_questions = 0
                for r in quiz_results:
                    if hasattr(r, 'total_questions') and r.total_questions > 0:
                        scores.append((r.score / r.total_questions) * 100)
                        total_questions += r.total_questions

                return {
                    'quizzes_played': total_played,
                    'average_score': round(sum(scores) / len(scores), 1) if scores else 0,
                    'best_score': round(max(scores), 1) if scores else 0,
                    'total_questions_answered': total_questions
                }
            else:
                # Estatísticas para moderadores/admins (quizzes criados)
                quizzes = getattr(self, 'quizzes', [])
                total_created = len(quizzes)
                active_quizzes = 0
                total_questions = 0
                total_plays = 0
                
                for q in quizzes:
                    if hasattr(q, 'is_active') and q.is_active and not getattr(q, 'is_deleted', False):
                        active_quizzes += 1
                    if hasattr(q, 'questions'):
                        total_questions += len(q.questions)
                    if hasattr(q, 'results'):
                        total_plays += len(q.results)

                return {
                    'quizzes_created': total_created,
                    'active_quizzes': active_quizzes,
                    'total_questions': total_questions,
                    'total_plays': total_plays
                }
        except Exception as e:
            # Em caso de erro, retornar estatísticas vazias
            print(f"Erro ao calcular estatísticas do usuário {self.id}: {e}")
            if self.is_student:
                return {
                    'quizzes_played': 0,
                    'average_score': 0,
                    'best_score': 0,
                    'total_questions_answered': 0
                }
            else:
                return {
                    'quizzes_created': 0,
                    'active_quizzes': 0,
                    'total_questions': 0,
                    'total_plays': 0
                }

    def __repr__(self):
        return f'<User {self.username} ({self.user_type})>'


class QuizResult(db.Model):
    """
    Modelo para armazenar resultados dos quizzes jogados
    """

    __tablename__ = 'quiz_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # Número de acertos
    total_questions = db.Column(db.Integer, nullable=False)  # Total de questões
    time_spent = db.Column(db.Integer, nullable=True)  # Tempo em segundos
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, quiz_id, score, total_questions, time_spent=None):
        self.user_id = user_id
        self.quiz_id = quiz_id
        self.score = score
        self.total_questions = total_questions
        self.time_spent = time_spent

    @property
    def percentage_score(self):
        """Retorna pontuação em percentual"""
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100, 1)

    @property
    def grade_letter(self):
        """Retorna nota em letra baseada na pontuação"""
        percentage = self.percentage_score
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'

    @property
    def grade_color(self):
        """Retorna cor da nota"""
        grade = self.grade_letter
        colors = {
            'A': 'success',  # Verde
            'B': 'info',  # Azul claro
            'C': 'warning',  # Amarelo
            'D': 'orange',  # Laranja
            'F': 'danger'  # Vermelho
        }
        return colors.get(grade, 'secondary')

    def get_time_display(self):
        """Retorna tempo formatado"""
        if not self.time_spent:
            return "Não registrado"

        minutes = self.time_spent // 60
        seconds = self.time_spent % 60

        if minutes > 0:
            return f"{minutes}min {seconds}s"
        else:
            return f"{seconds}s"

    def __repr__(self):
        return f'<QuizResult {self.user_id}-{self.quiz_id}: {self.score}/{self.total_questions}>'
