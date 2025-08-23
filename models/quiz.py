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
from flask import current_app
from flask_sqlalchemy import SQLAlchemy

# Obter instância do SQLAlchemy do Flask de forma segura
def get_db():
    return current_app.extensions['sqlalchemy']


class Quiz:
    """
    Modelo de quiz do sistema Brainchild
    """

    def __init__(self):
        # Obter db dinamicamente para evitar importação circular
        self.db = get_db()
        self.__tablename__ = 'quizzes'

    @classmethod
    def create_table(cls, db):
        """Cria tabela dinamicamente"""
        return db.Table('quizzes',
            db.Column('id', db.Integer, primary_key=True),
            db.Column('title', db.String(200), nullable=False),
            db.Column('description', db.Text, nullable=True),
            db.Column('created_by', db.Integer, db.ForeignKey('users.id'), nullable=False),
            db.Column('created_at', db.DateTime, default=datetime.utcnow),
            db.Column('updated_at', db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            
            # Sistema de status simplificado
            db.Column('is_active', db.Boolean, default=True, nullable=False),
            db.Column('is_archived', db.Boolean, default=False, nullable=False),
            db.Column('is_deleted', db.Boolean, default=False, nullable=False),
            
            # Configurações opcionais
            db.Column('image_filename', db.String(255), nullable=True),
            db.Column('time_limit', db.Integer, nullable=True),
            db.Column('shuffle_questions', db.Boolean, default=True),
            db.Column('shuffle_answers', db.Boolean, default=True)
        )

    def __init__(self, title, description, created_by, image_filename=None, time_limit=None):
        self.title = title
        self.description = description
        self.created_by = created_by
        self.image_filename = image_filename
        self.time_limit = time_limit
        self.is_active = True
        self.is_archived = False
        self.is_deleted = False
        self.shuffle_questions = True
        self.shuffle_answers = True
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    @property
    def question_count(self):
        """Retorna o número de questões do quiz"""
        try:
            from models.question import Question
            return Question.query.filter_by(quiz_id=self.id).count()
        except:
            return 0

    @property 
    def creator(self):
        """Retorna o criador do quiz"""
        try:
            from models.user import User
            return User.query.get(self.created_by)
        except:
            return None

    @property
    def status(self):
        """Retorna status baseado nos campos booleanos"""
        if self.is_deleted:
            return 'deleted'
        elif self.is_archived:
            return 'archived'
        elif self.is_active:
            return 'active'
        else:
            return 'inactive'

    def get_questions(self):
        """Retorna questões do quiz"""
        try:
            from models.question import Question
            return Question.query.filter_by(quiz_id=self.id).order_by(Question.order_index).all()
        except:
            return []

    def can_be_played(self):
        """Verifica se o quiz pode ser jogado"""
        return (self.is_active and 
                not self.is_archived and 
                not self.is_deleted and
                self.question_count > 0)

    def can_be_edited(self):
        """Verifica se pode ser editado"""
        return not self.is_deleted

    def get_questions_for_play(self):
        """Retorna questões preparadas para jogar"""
        prepared_questions = []
        
        try:
            questions = self.get_questions()
            if self.shuffle_questions:
                random.shuffle(questions)

            for index, question in enumerate(questions):
                # Criar alternativas
                alternatives = []

                # Resposta correta
                alternatives.append({
                    'text': question.correct_answer,
                    'is_correct': True,
                    'letter': 'A'
                })

                # Respostas incorretas
                incorrect_options = []
                for option in [question.option_a, question.option_b, question.option_c]:
                    if option and option.strip():
                        incorrect_options.append(option)

                for option in incorrect_options:
                    alternatives.append({
                        'text': option,
                        'is_correct': False,
                        'letter': 'A'
                    })

                # Embaralhar respostas
                if self.shuffle_answers:
                    random.shuffle(alternatives)

                # Atribuir letras
                letters = ['A', 'B', 'C', 'D']
                correct_letter = None
                
                for i, alternative in enumerate(alternatives):
                    alternative['letter'] = letters[i] if i < len(letters) else str(i + 1)
                    if alternative['is_correct']:
                        correct_letter = alternative['letter']

                question_data = {
                    'id': question.id,
                    'text': question.question_text,
                    'image_filename': question.image_filename,
                    'alternatives': alternatives,
                    'correct_letter': correct_letter,
                    'order_index': index + 1
                }

                prepared_questions.append(question_data)

        except Exception as e:
            print(f"Erro ao preparar questões: {e}")

        return prepared_questions

    def archive(self):
        """Arquiva o quiz"""
        try:
            db = get_db()
            self.is_archived = True
            self.is_active = False
            self.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        """Marca como excluído"""
        try:
            db = get_db()
            self.is_deleted = True
            self.is_active = False
            self.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def restore(self):
        """Restaura quiz"""
        try:
            db = get_db()
            self.is_deleted = False
            self.is_archived = False
            self.is_active = True
            self.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def get_completion_stats(self):
        """Retorna estatísticas"""
        try:
            from models.user import QuizResult
            results = QuizResult.query.filter_by(quiz_id=self.id).all()
            
            if not results:
                return {
                    'total_attempts': 0,
                    'average_score': 0,
                    'best_score': 0,
                    'worst_score': 0,
                    'completion_rate': 0,
                    'average_time': 0
                }

            percentages = [r.percentage_score for r in results if hasattr(r, 'percentage_score')]
            times = [r.time_spent for r in results if hasattr(r, 'time_spent') and r.time_spent]

            return {
                'total_attempts': len(results),
                'average_score': round(sum(percentages) / len(percentages), 1) if percentages else 0,
                'best_score': max(percentages) if percentages else 0,
                'worst_score': min(percentages) if percentages else 0,
                'completion_rate': 100,
                'average_time': round(sum(times) / len(times), 0) if times else 0
            }
        except:
            return {
                'total_attempts': 0, 'average_score': 0, 'best_score': 0,
                'worst_score': 0, 'completion_rate': 0, 'average_time': 0
            }

    def has_image(self):
        """Verifica se tem imagem"""
        return self.image_filename is not None and self.image_filename.strip() != ''

    def get_status_display(self):
        """Status em português"""
        statuses = {
            'active': 'Ativo',
            'inactive': 'Inativo', 
            'archived': 'Arquivado',
            'deleted': 'Excluído'
        }
        return statuses.get(self.status, 'Desconhecido')

    def get_status_color(self):
        """Cor do badge do status"""
        colors = {
            'active': 'success',
            'inactive': 'warning',
            'archived': 'secondary', 
            'deleted': 'danger'
        }
        return colors.get(self.status, 'light')

    def __repr__(self):
        return f'<Quiz {self.title} ({self.status})>'


# Modelo compatível com SQLAlchemy tradicional
try:
    from app import db
    
    class Quiz(db.Model):
        __tablename__ = 'quizzes'

        # Campos básicos
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text, nullable=True)
        created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        # Sistema de status
        is_active = db.Column(db.Boolean, default=True, nullable=False)
        is_archived = db.Column(db.Boolean, default=False, nullable=False)
        is_deleted = db.Column(db.Boolean, default=False, nullable=False)

        # Configurações
        image_filename = db.Column(db.String(255), nullable=True)
        time_limit = db.Column(db.Integer, nullable=True)
        shuffle_questions = db.Column(db.Boolean, default=True)
        shuffle_answers = db.Column(db.Boolean, default=True)

        # Relacionamentos
        questions = db.relationship('Question', backref='quiz', lazy=True, 
                                   cascade='all, delete-orphan',
                                   order_by='Question.order_index')
        
        def __init__(self, title, description, created_by, image_filename=None, time_limit=None):
            self.title = title
            self.description = description
            self.created_by = created_by
            self.image_filename = image_filename
            self.time_limit = time_limit

        @property
        def question_count(self):
            try:
                return len(self.questions) if self.questions else 0
            except:
                return 0

        @property
        def creator(self):
            try:
                from models.user import User
                return User.query.get(self.created_by)
            except:
                return None

        @property
        def status(self):
            if self.is_deleted:
                return 'deleted'
            elif self.is_archived:
                return 'archived'
            elif self.is_active:
                return 'active'
            else:
                return 'inactive'

        def can_be_played(self):
            return (self.is_active and 
                    not self.is_archived and 
                    not self.is_deleted and
                    self.question_count > 0)

        def get_questions_for_play(self):
            prepared_questions = []
            
            try:
                questions = list(self.questions) if self.questions else []
                if self.shuffle_questions:
                    random.shuffle(questions)

                for index, question in enumerate(questions):
                    alternatives = []

                    alternatives.append({
                        'text': question.correct_answer,
                        'is_correct': True,
                        'letter': 'A'
                    })

                    incorrect_options = []
                    for option in [question.option_a, question.option_b, question.option_c]:
                        if option and option.strip():
                            incorrect_options.append(option)

                    for option in incorrect_options:
                        alternatives.append({
                            'text': option,
                            'is_correct': False,
                            'letter': 'A'
                        })

                    if self.shuffle_answers:
                        random.shuffle(alternatives)

                    letters = ['A', 'B', 'C', 'D']
                    correct_letter = None
                    
                    for i, alternative in enumerate(alternatives):
                        alternative['letter'] = letters[i] if i < len(letters) else str(i + 1)
                        if alternative['is_correct']:
                            correct_letter = alternative['letter']

                    question_data = {
                        'id': question.id,
                        'text': question.question_text,
                        'image_filename': question.image_filename,
                        'alternatives': alternatives,
                        'correct_letter': correct_letter,
                        'order_index': index + 1
                    }

                    prepared_questions.append(question_data)

            except Exception as e:
                print(f"Erro ao preparar questões: {e}")

            return prepared_questions

        def get_status_display(self):
            statuses = {
                'active': 'Ativo',
                'inactive': 'Inativo',
                'archived': 'Arquivado', 
                'deleted': 'Excluído'
            }
            return statuses.get(self.status, 'Desconhecido')

        def get_status_color(self):
            colors = {
                'active': 'success',
                'inactive': 'warning',
                'archived': 'secondary',
                'deleted': 'danger'
            }
            return colors.get(self.status, 'light')

        def has_image(self):
            return self.image_filename is not None and self.image_filename.strip() != ''

        def __repr__(self):
            return f'<Quiz {self.title} ({self.status})>'

except ImportError:
    # Se não conseguir importar, usar modelo básico
    pass
