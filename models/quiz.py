"""
Modelo de Quizzes - Brainchild
==============================

Define a estrutura dos quizzes com:
- Sistema de status (ativo, arquivado, excluído)
- Embaralhamento automático de respostas
- Estatísticas de desempenho
- Upload de imagens
"""
from datetime import datetime
import random
from sqlalchemy import desc, func
from sqlalchemy.orm import relationship

# Importação correta sem circular reference
try:
    from app import db
except ImportError:
    db = None

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    difficulty = db.Column(db.String(20), default='medium')
    time_limit = db.Column(db.Integer)  # em minutos
    
    # Sistema de status
    status = db.Column(db.String(20), default='active')  # active, archived, deleted
    is_public = db.Column(db.Boolean, default=True)
    
    # Configurações
    shuffle_questions = db.Column(db.Boolean, default=True)
    shuffle_answers = db.Column(db.Boolean, default=True)
    allow_retries = db.Column(db.Boolean, default=True)
    show_correct_answers = db.Column(db.Boolean, default=True)
    
    # Metadados
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Estatísticas
    total_attempts = db.Column(db.Integer, default=0)
    total_completions = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0.0)
    
    # Upload de imagem
    image_filename = db.Column(db.String(255))
    
    # Relacionamentos (com lazy loading para evitar problemas)
    questions = relationship('Question', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Quiz, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    @property
    def creator(self):
        """Propriedade segura para acessar o criador do quiz"""
        try:
            from models.user import User
            return User.query.get(self.created_by)
        except:
            return None
    
    @property
    def question_count(self):
        """Conta o número de questões ativas"""
        return self.questions.count()
    
    @property
    def is_active(self):
        """Verifica se o quiz está ativo"""
        return self.status == 'active'
    
    @property
    def is_archived(self):
        """Verifica se o quiz está arquivado"""
        return self.status == 'archived'
    
    @property
    def completion_rate(self):
        """Calcula a taxa de conclusão"""
        if self.total_attempts == 0:
            return 0
        return round((self.total_completions / self.total_attempts) * 100, 1)
    
    def get_questions_for_play(self):
        """Retorna questões para jogar, com embaralhamento se configurado"""
        questions = list(self.questions.filter_by(is_active=True).order_by('order_index'))
        
        if self.shuffle_questions:
            random.shuffle(questions)
        
        return questions
    
    def archive(self):
        """Arquiva o quiz"""
        try:
            self.status = 'archived'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def restore(self):
        """Restaura quiz arquivado"""
        try:
            self.status = 'active'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def soft_delete(self):
        """Exclusão lógica do quiz"""
        try:
            self.status = 'deleted'
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def update_stats(self, score, completed=True):
        """Atualiza estatísticas após uma tentativa"""
        try:
            self.total_attempts += 1
            
            if completed:
                self.total_completions += 1
                
                # Recalcula média ponderada
                if self.total_completions == 1:
                    self.average_score = score
                else:
                    total_score = (self.average_score * (self.total_completions - 1)) + score
                    self.average_score = round(total_score / self.total_completions, 2)
            
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_completion_stats(self):
        """Retorna estatísticas de conclusão seguras"""
        try:
            from models.quiz_result import QuizResult
            
            # Resultados dos últimos 30 dias
            thirty_days_ago = datetime.utcnow().replace(day=1)  # Simplificado
            
            recent_results = QuizResult.query.filter(
                QuizResult.quiz_id == self.id,
                QuizResult.completed_at >= thirty_days_ago
            ).all()
            
            if not recent_results:
                return {
                    'total_attempts': 0,
                    'completions': 0,
                    'completion_rate': 0,
                    'average_score': 0,
                    'best_score': 0
                }
            
            completed = [r for r in recent_results if r.is_completed]
            scores = [r.score for r in completed if r.score is not None]
            
            return {
                'total_attempts': len(recent_results),
                'completions': len(completed),
                'completion_rate': round((len(completed) / len(recent_results)) * 100, 1) if recent_results else 0,
                'average_score': round(sum(scores) / len(scores), 1) if scores else 0,
                'best_score': max(scores) if scores else 0
            }
        except Exception as e:
            return {
                'total_attempts': self.total_attempts,
                'completions': self.total_completions,
                'completion_rate': self.completion_rate,
                'average_score': self.average_score,
                'best_score': 0
            }
    
    def get_recent_results(self, limit=5):
        """Retorna resultados recentes seguros"""
        try:
            from models.quiz_result import QuizResult
            
            return QuizResult.query.filter_by(quiz_id=self.id)\
                                 .filter(QuizResult.is_completed == True)\
                                 .order_by(desc(QuizResult.completed_at))\
                                 .limit(limit).all()
        except Exception as e:
            return []
    
    @staticmethod
    def get_popular_quizzes(limit=5):
        """Retorna quizzes mais populares de forma segura"""
        try:
            return Quiz.query.filter_by(status='active', is_public=True)\
                           .order_by(desc(Quiz.total_attempts))\
                           .limit(limit).all()
        except Exception as e:
            return []
    
    @staticmethod
    def get_recent_quizzes(limit=5):
        """Retorna quizzes mais recentes"""
        try:
            return Quiz.query.filter_by(status='active')\
                           .order_by(desc(Quiz.created_at))\
                           .limit(limit).all()
        except Exception as e:
            return []
    
    def __repr__(self):
        return f'<Quiz {self.title}>'
