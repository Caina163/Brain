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
from flask import current_app

# Usar current_app.extensions['sqlalchemy'] em vez de importação circular
def get_db():
    return current_app.extensions['sqlalchemy']

db = SQLAlchemy()

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

    # Relacionamentos com outras tabelas
    quizzes = db.relationship('Quiz', backref='creator', lazy=True, cascade='all, delete-orphan')
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True, cascade='all, delete-orphan')

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
        if self.is_student:
            # Estatísticas para alunos (quizzes jogados)
            total_played = len(self.quiz_results)
            if total_played == 0:
                return {
                    'quizzes_played': 0,
                    'average_score': 0,
                    'best_score': 0,
                    'total_questions_answered': 0
                }

            scores = [(r.score / r.total_questions) * 100 for r in self.quiz_results if r.total_questions > 0]
            total_questions = sum(r.total_questions for r in self.quiz_results)

            return {
                'quizzes_played': total_played,
                'average_score': round(sum(scores) / len(scores), 1) if scores else 0,
                'best_score': round(max(scores), 1) if scores else 0,
                'total_questions_answered': total_questions
            }
        else:
            # Estatísticas para moderadores/admins (quizzes criados)
            total_created = len(self.quizzes)
            active_quizzes = len([q for q in self.quizzes if getattr(q, 'is_active', True) and not getattr(q, 'is_deleted', False)])

            return {
                'quizzes_created': total_created,
                'active_quizzes': active_quizzes,
                'total_questions': sum(len(getattr(q, 'questions', [])) for q in self.quizzes),
                'total_plays': sum(len(getattr(q, 'results', [])) for q in self.quizzes)
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
