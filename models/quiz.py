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

# Importação segura do SQLAlchemy
try:
    from app import db
except ImportError:
    db = None


class Quiz(db.Model):
    """
    Modelo de quiz do sistema Brainchild
    """

    __tablename__ = 'quizzes'

    # Campos da tabela
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Sistema de status do quiz - NOVO SISTEMA
    status = db.Column(db.String(20), default='active', nullable=False)  # active, archived, deleted
    is_public = db.Column(db.Boolean, default=True, nullable=False)

    # Imagem do quiz (opcional)
    image_filename = db.Column(db.String(255), nullable=True)

    # Configurações do quiz
    time_limit = db.Column(db.Integer, nullable=True)  # Tempo limite em minutos
    shuffle_questions = db.Column(db.Boolean, default=True)  # Embaralhar questões
    shuffle_answers = db.Column(db.Boolean, default=True)  # Embaralhar respostas

    # Relacionamentos
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan',
                                order_by='Question.order_index')
    results = db.relationship('QuizResult', backref='quiz', lazy=True, cascade='all, delete-orphan')

    def __init__(self, title, description, created_by, image_filename=None, time_limit=None):
        self.title = title
        self.description = description
        self.created_by = created_by
        self.image_filename = image_filename
        self.time_limit = time_limit
        self.status = 'active'
        self.is_public = True

    @property
    def question_count(self):
        """Retorna o número de questões do quiz"""
        try:
            return len(self.questions) if self.questions else 0
        except Exception:
            return 0

    def get_creator(self):
        """Retorna o criador do quiz com proteção contra erros"""
        try:
            from models.user import User
            return User.query.get(self.created_by)
        except Exception:
            return None

    def get_questions(self):
        """Retorna lista de questões com fallback seguro"""
        try:
            return list(self.questions) if self.questions else []
        except Exception:
            return []

    def get_results(self):
        """Retorna lista de resultados com fallback seguro"""
        try:
            return list(self.results) if self.results else []
        except Exception:
            return []

    # Propriedades de compatibilidade com sistema antigo
    @property
    def is_active(self):
        """Compatibilidade - verifica se está ativo"""
        return self.status == 'active'

    @property
    def is_archived(self):
        """Compatibilidade - verifica se está arquivado"""
        return self.status == 'archived'

    @property
    def is_deleted(self):
        """Compatibilidade - verifica se está excluído"""
        return self.status == 'deleted'

    def get_status_display(self):
        """Retorna o status em português"""
        statuses = {
            'active': 'Ativo',
            'inactive': 'Inativo',
            'archived': 'Arquivado',
            'deleted': 'Excluído'
        }
        return statuses.get(self.status, 'Desconhecido')

    def get_status_color(self):
        """Retorna a cor do badge do status"""
        colors = {
            'active': 'success',
            'inactive': 'warning',
            'archived': 'secondary',
            'deleted': 'danger'
        }
        return colors.get(self.status, 'light')

    def can_be_played(self):
        """Verifica se o quiz pode ser jogado"""
        return (self.status == 'active' and 
                self.is_public and
                self.question_count > 0)

    def can_be_edited(self):
        """Verifica se o quiz pode ser editado"""
        return self.status != 'deleted'

    def get_questions_for_play(self):
        """
        Retorna questões preparadas para jogar com respostas embaralhadas
        IMPORTANTE: A resposta correta sempre alterna de posição
        """
        prepared_questions = []

        try:
            questions = self.get_questions()
            if self.shuffle_questions:
                random.shuffle(questions)

            for index, question in enumerate(questions):
                # Criar lista de alternativas
                alternatives = []

                # Sempre adicionar a resposta correta primeiro
                alternatives.append({
                    'text': question.correct_answer,
                    'is_correct': True,
                    'letter': 'A'  # Temporário, será ajustado depois
                })

                # Adicionar alternativas incorretas
                incorrect_options = []
                if question.option_a and question.option_a.strip():
                    incorrect_options.append(question.option_a)
                if question.option_b and question.option_b.strip():
                    incorrect_options.append(question.option_b)
                if question.option_c and question.option_c.strip():
                    incorrect_options.append(question.option_c)

                for option in incorrect_options:
                    alternatives.append({
                        'text': option,
                        'is_correct': False,
                        'letter': 'A'  # Temporário
                    })

                # EMBARALHAR RESPOSTAS - A resposta correta ficará em posição aleatória
                if self.shuffle_answers:
                    random.shuffle(alternatives)

                # Atribuir letras às alternativas (A, B, C, D)
                letters = ['A', 'B', 'C', 'D']
                for i, alternative in enumerate(alternatives):
                    alternative['letter'] = letters[i] if i < len(letters) else str(i + 1)
                    alternative['index'] = i

                # Encontrar qual letra é a resposta correta
                correct_letter = None
                for alt in alternatives:
                    if alt['is_correct']:
                        correct_letter = alt['letter']
                        break

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
            self.status = 'archived'
            self.updated_at = datetime.utcnow()
            if db:
                db.session.commit()
        except Exception as e:
            if db:
                db.session.rollback()
            raise e

    def delete(self):
        """Marca o quiz como excluído (soft delete)"""
        try:
            self.status = 'deleted'
            self.updated_at = datetime.utcnow()
            if db:
                db.session.commit()
        except Exception as e:
            if db:
                db.session.rollback()
            raise e

    def restore(self):
        """Restaura quiz arquivado ou excluído"""
        try:
            self.status = 'active'
            self.updated_at = datetime.utcnow()
            if db:
                db.session.commit()
        except Exception as e:
            if db:
                db.session.rollback()
            raise e

    def activate(self):
        """Ativa quiz inativo"""
        try:
            if self.status != 'deleted':
                self.status = 'active'
                self.updated_at = datetime.utcnow()
                if db:
                    db.session.commit()
        except Exception as e:
            if db:
                db.session.rollback()
            raise e

    def deactivate(self):
        """Desativa quiz ativo"""
        try:
            self.status = 'inactive'
            self.updated_at = datetime.utcnow()
            if db:
                db.session.commit()
        except Exception as e:
            if db:
                db.session.rollback()
            raise e

    def get_completion_stats(self):
        """Retorna estatísticas de conclusão do quiz"""
        try:
            results = self.get_results()
            total_attempts = len(results)
            if total_attempts == 0:
                return {
                    'total_attempts': 0,
                    'average_score': 0,
                    'best_score': 0,
                    'worst_score': 0,
                    'completion_rate': 0,
                    'average_time': 0
                }

            scores = [result.score for result in results if hasattr(result, 'score')]
            percentages = [result.percentage_score for result in results if hasattr(result, 'percentage_score')]
            times = [result.time_spent for result in results if hasattr(result, 'time_spent') and result.time_spent]

            stats = {
                'total_attempts': total_attempts,
                'average_score': round(sum(percentages) / len(percentages), 1) if percentages else 0,
                'best_score': max(percentages) if percentages else 0,
                'worst_score': min(percentages) if percentages else 0,
                'completion_rate': 100,  # Como só salvamos resultados completos
                'average_time': round(sum(times) / len(times), 0) if times else 0
            }

            return stats
        except Exception:
            return {
                'total_attempts': 0,
                'average_score': 0,
                'best_score': 0,
                'worst_score': 0,
                'completion_rate': 0,
                'average_time': 0
            }

    def get_recent_results(self, limit=5):
        """Retorna resultados recentes do quiz"""
        try:
            from models.user import QuizResult
            return (QuizResult.query
                    .filter_by(quiz_id=self.id)
                    .order_by(QuizResult.completed_at.desc())
                    .limit(limit)
                    .all())
        except Exception:
            return []

    def get_top_performers(self, limit=5):
        """Retorna top performers do quiz"""
        try:
            from models.user import QuizResult
            return (QuizResult.query
                    .filter_by(quiz_id=self.id)
                    .order_by(QuizResult.score.desc(), QuizResult.time_spent.asc())
                    .limit(limit)
                    .all())
        except Exception:
            return []

    def has_image(self):
        """Verifica se o quiz tem imagem"""
        return self.image_filename is not None and self.image_filename.strip() != ''

    def get_difficulty_level(self):
        """Calcula nível de dificuldade baseado nas estatísticas"""
        try:
            stats = self.get_completion_stats()
            if stats['total_attempts'] < 5:
                return 'Não definido'

            avg_score = stats['average_score']
            if avg_score >= 80:
                return 'Fácil'
            elif avg_score >= 60:
                return 'Médio'
            elif avg_score >= 40:
                return 'Difícil'
            else:
                return 'Muito Difícil'
        except Exception:
            return 'Não definido'

    def get_difficulty_color(self):
        """Retorna cor do nível de dificuldade"""
        difficulty = self.get_difficulty_level()
        colors = {
            'Fácil': 'success',
            'Médio': 'warning',
            'Difícil': 'orange',
            'Muito Difícil': 'danger',
            'Não definido': 'secondary'
        }
        return colors.get(difficulty, 'secondary')

    def calculate_estimated_time(self):
        """Calcula tempo estimado baseado no número de questões"""
        # Estimativa: 1 minuto por questão + 30 segundos de buffer
        base_time = self.question_count * 1.5
        return max(base_time, 2)  # Mínimo 2 minutos

    # Métodos estáticos para queries comuns
    @staticmethod
    def get_active_quizzes():
        """Retorna todos os quizzes ativos"""
        try:
            return Quiz.query.filter_by(status='active', is_public=True).all()
        except Exception:
            return []

    @staticmethod
    def get_user_quizzes(user_id):
        """Retorna quizzes criados por um usuário"""
        try:
            return Quiz.query.filter_by(created_by=user_id).all()
        except Exception:
            return []

    def __repr__(self):
        return f'<Quiz {self.title} ({self.status})>'
