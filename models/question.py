"""
Modelo de Questões - Brainchild
===============================

Define a estrutura das questões dos quizzes com:
- Suporte a imagens
- Resposta correta + até 3 alternativas incorretas
- Sistema de ordenação
- Validação de respostas
"""
from datetime import datetime
import random

# Importação correta sem circular reference
try:
    from app import db
except ImportError:
    db = None

class Question(db.Model):
    __tablename__ = 'questions'
    
    # Campos principais
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    
    # Sistema de respostas
    correct_answer = db.Column(db.String(500), nullable=False)
    wrong_answer_1 = db.Column(db.String(500))
    wrong_answer_2 = db.Column(db.String(500))
    wrong_answer_3 = db.Column(db.String(500))
    
    # Configurações
    order_index = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=1)
    time_limit = db.Column(db.Integer)  # em segundos
    
    # Upload de imagem
    image_filename = db.Column(db.String(255))
    
    # Metadados
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Estatísticas
    total_attempts = db.Column(db.Integer, default=0)
    correct_attempts = db.Column(db.Integer, default=0)
    
    def __init__(self, **kwargs):
        super(Question, self).__init__(**kwargs)
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    @property
    def difficulty_rate(self):
        """Calcula a taxa de dificuldade (% de erros)"""
        if self.total_attempts == 0:
            return 0
        return round(((self.total_attempts - self.correct_attempts) / self.total_attempts) * 100, 1)
    
    @property
    def success_rate(self):
        """Calcula a taxa de sucesso (% de acertos)"""
        if self.total_attempts == 0:
            return 0
        return round((self.correct_attempts / self.total_attempts) * 100, 1)
    
    def get_all_answers(self, shuffle=True):
        """Retorna todas as respostas possíveis"""
        answers = [self.correct_answer]
        
        # Adiciona respostas incorretas que existem
        if self.wrong_answer_1:
            answers.append(self.wrong_answer_1)
        if self.wrong_answer_2:
            answers.append(self.wrong_answer_2)
        if self.wrong_answer_3:
            answers.append(self.wrong_answer_3)
        
        # Embaralha se solicitado
        if shuffle:
            random.shuffle(answers)
            
        return answers
    
    def get_wrong_answers(self):
        """Retorna apenas as respostas incorretas"""
        wrong_answers = []
        
        if self.wrong_answer_1:
            wrong_answers.append(self.wrong_answer_1)
        if self.wrong_answer_2:
            wrong_answers.append(self.wrong_answer_2)
        if self.wrong_answer_3:
            wrong_answers.append(self.wrong_answer_3)
            
        return wrong_answers
    
    def is_correct_answer(self, answer):
        """Verifica se a resposta está correta"""
        if not answer:
            return False
        return answer.strip().lower() == self.correct_answer.strip().lower()
    
    def record_attempt(self, is_correct):
        """Registra uma tentativa de resposta"""
        try:
            self.total_attempts += 1
            if is_correct:
                self.correct_attempts += 1
            
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def move_up(self):
        """Move a questão uma posição para cima"""
        try:
            # Encontra a questão anterior
            previous_question = Question.query.filter(
                Question.quiz_id == self.quiz_id,
                Question.order_index < self.order_index,
                Question.is_active == True
            ).order_by(Question.order_index.desc()).first()
            
            if previous_question:
                # Troca as posições
                temp_order = self.order_index
                self.order_index = previous_question.order_index
                previous_question.order_index = temp_order
                
                # Atualiza timestamps
                self.updated_at = datetime.utcnow()
                previous_question.updated_at = datetime.utcnow()
                
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            return False
    
    def move_down(self):
        """Move a questão uma posição para baixo"""
        try:
            # Encontra a próxima questão
            next_question = Question.query.filter(
                Question.quiz_id == self.quiz_id,
                Question.order_index > self.order_index,
                Question.is_active == True
            ).order_by(Question.order_index.asc()).first()
            
            if next_question:
                # Troca as posições
                temp_order = self.order_index
                self.order_index = next_question.order_index
                next_question.order_index = temp_order
                
                # Atualiza timestamps
                self.updated_at = datetime.utcnow()
                next_question.updated_at = datetime.utcnow()
                
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            return False
    
    def duplicate(self):
        """Cria uma cópia da questão"""
        try:
            # Conta questões do quiz para definir nova posição
            max_order = db.session.query(db.func.max(Question.order_index))\
                                .filter_by(quiz_id=self.quiz_id, is_active=True)\
                                .scalar() or 0
            
            # Cria nova questão
            new_question = Question(
                quiz_id=self.quiz_id,
                question_text=f"{self.question_text} (Cópia)",
                correct_answer=self.correct_answer,
                wrong_answer_1=self.wrong_answer_1,
                wrong_answer_2=self.wrong_answer_2,
                wrong_answer_3=self.wrong_answer_3,
                order_index=max_order + 1,
                points=self.points,
                time_limit=self.time_limit,
                image_filename=self.image_filename
            )
            
            db.session.add(new_question)
            db.session.commit()
            return new_question
        except Exception as e:
            db.session.rollback()
            return None
    
    def soft_delete(self):
        """Exclusão lógica da questão"""
        try:
            self.is_active = False
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def restore(self):
        """Restaura questão excluída logicamente"""
        try:
            self.is_active = True
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    def update_order_in_quiz(self):
        """Reorganiza a ordem das questões após alterações"""
        try:
            questions = Question.query.filter_by(
                quiz_id=self.quiz_id, 
                is_active=True
            ).order_by(Question.order_index).all()
            
            # Reordena sequencialmente
            for i, question in enumerate(questions, 1):
                if question.order_index != i:
                    question.order_index = i
                    question.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_next_order_index(quiz_id):
        """Retorna o próximo índice de ordenação para um quiz"""
        try:
            max_order = db.session.query(db.func.max(Question.order_index))\
                                .filter_by(quiz_id=quiz_id, is_active=True)\
                                .scalar()
            return (max_order or 0) + 1
        except Exception as e:
            return 1
    
    @staticmethod
    def get_quiz_questions(quiz_id, include_inactive=False):
        """Retorna todas as questões de um quiz"""
        try:
            query = Question.query.filter_by(quiz_id=quiz_id)
            
            if not include_inactive:
                query = query.filter_by(is_active=True)
                
            return query.order_by(Question.order_index).all()
        except Exception as e:
            return []
    
    def to_dict(self):
        """Converte questão para dicionário (útil para JSON)"""
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'correct_answer': self.correct_answer,
            'wrong_answers': self.get_wrong_answers(),
            'all_answers': self.get_all_answers(),
            'order_index': self.order_index,
            'points': self.points,
            'time_limit': self.time_limit,
            'image_filename': self.image_filename,
            'success_rate': self.success_rate,
            'difficulty_rate': self.difficulty_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:50]}...>'
