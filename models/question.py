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
from flask import current_app
from flask_sqlalchemy import SQLAlchemy

# Obter instância do SQLAlchemy do Flask
def get_db():
    return current_app.extensions['sqlalchemy']

db = get_db()


class Question(db.Model):
    """
    Modelo de questão do sistema Brainchild
    """

    __tablename__ = 'questions'

    # Campos da tabela
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)

    # Sistema de respostas
    correct_answer = db.Column(db.String(500), nullable=False)  # Resposta correta (sempre primeira)
    option_a = db.Column(db.String(500), nullable=True)  # Alternativa incorreta 1
    option_b = db.Column(db.String(500), nullable=True)  # Alternativa incorreta 2
    option_c = db.Column(db.String(500), nullable=True)  # Alternativa incorreta 3

    # Imagem da questão (opcional)
    image_filename = db.Column(db.String(255), nullable=True)

    # Controle de ordem e timestamps
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, quiz_id, question_text, correct_answer, option_a=None, option_b=None, option_c=None,
                 image_filename=None, order_index=0):
        self.quiz_id = quiz_id
        self.question_text = question_text
        self.correct_answer = correct_answer
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.image_filename = image_filename
        self.order_index = order_index

    def get_all_options(self):
        """Retorna todas as opções de resposta (incluindo a correta)"""
        options = [self.correct_answer]

        if self.option_a and self.option_a.strip():
            options.append(self.option_a)
        if self.option_b and self.option_b.strip():
            options.append(self.option_b)
        if self.option_c and self.option_c.strip():
            options.append(self.option_c)

        return options

    def get_incorrect_options(self):
        """Retorna apenas as opções incorretas"""
        options = []

        if self.option_a and self.option_a.strip():
            options.append(self.option_a)
        if self.option_b and self.option_b.strip():
            options.append(self.option_b)
        if self.option_c and self.option_c.strip():
            options.append(self.option_c)

        return options

    def is_answer_correct(self, answer):
        """Verifica se a resposta fornecida está correta"""
        if not answer:
            return False

        # Normalizar strings para comparação (remover espaços e converter para minúsculo)
        correct = self.correct_answer.strip().lower()
        provided = answer.strip().lower()

        return correct == provided

    def validate_answer_by_letter(self, letter, alternatives_list):
        """
        Valida resposta pela letra escolhida
        alternatives_list deve ser o resultado de get_questions_for_play()
        """
        if not letter or not alternatives_list:
            return False

        # Encontrar a alternativa correspondente à letra
        for alternative in alternatives_list:
            if alternative['letter'].upper() == letter.upper():
                return alternative['is_correct']

        return False

    @property
    def options_count(self):
        """Retorna o número de opções disponíveis (incluindo resposta correta)"""
        count = 1  # Resposta correta sempre existe

        if self.option_a and self.option_a.strip():
            count += 1
        if self.option_b and self.option_b.strip():
            count += 1
        if self.option_c and self.option_c.strip():
            count += 1

        return count

    def has_image(self):
        """Verifica se a questão tem imagem"""
        return self.image_filename is not None and self.image_filename.strip() != ''

    def get_formatted_question(self):
        """Retorna a questão formatada com quebras de linha convertidas para HTML"""
        if not self.question_text:
            return ""

        # Converter quebras de linha para HTML
        formatted = self.question_text.replace('\n', '<br>')
        return formatted

    def get_question_preview(self, max_length=100):
        """Retorna preview da questão para listagens"""
        if not self.question_text:
            return "Questão sem texto"

        text = self.question_text.strip()
        if len(text) <= max_length:
            return text

        # Truncar e adicionar reticências
        return text[:max_length].rsplit(' ', 1)[0] + '...'

    def validate_options(self):
        """Valida se a questão tem pelo menos 2 opções (1 correta + 1 incorreta)"""
        incorrect_count = len(self.get_incorrect_options())
        return incorrect_count >= 1  # Mínimo 1 alternativa incorreta + resposta correta

    def get_difficulty_estimate(self):
        """Estima dificuldade baseada no comprimento do texto e número de opções"""
        text_length = len(self.question_text) if self.question_text else 0
        options_count = self.options_count
        has_img = self.has_image()

        # Cálculo simples de dificuldade
        difficulty_score = 0

        # Baseado no texto
        if text_length > 200:
            difficulty_score += 2
        elif text_length > 100:
            difficulty_score += 1

        # Baseado no número de opções
        if options_count >= 4:
            difficulty_score += 2
        elif options_count == 3:
            difficulty_score += 1

        # Se tem imagem, pode ser mais fácil (visual) ou mais difícil (interpretação)
        if has_img:
            difficulty_score += 1

        # Classificar dificuldade
        if difficulty_score >= 4:
            return 'Difícil'
        elif difficulty_score >= 2:
            return 'Médio'
        else:
            return 'Fácil'

    def get_difficulty_color(self):
        """Retorna cor da dificuldade"""
        difficulty = self.get_difficulty_estimate()
        colors = {
            'Fácil': 'success',
            'Médio': 'warning',
            'Difícil': 'danger'
        }
        return colors.get(difficulty, 'secondary')

    def duplicate_to_quiz(self, target_quiz_id):
        """Duplica questão para outro quiz"""
        try:
            db = current_app.extensions['sqlalchemy']
            new_question = Question(
                quiz_id=target_quiz_id,
                question_text=self.question_text,
                correct_answer=self.correct_answer,
                option_a=self.option_a,
                option_b=self.option_b,
                option_c=self.option_c,
                image_filename=self.image_filename,  # Nota: a imagem também seria copiada
                order_index=0  # Será ajustado conforme necessário
            )

            db.session.add(new_question)
            return new_question
        except Exception as e:
            print(f"Erro ao duplicar questão: {e}")
            return None

    def move_up(self):
        """Move questão para cima na ordem"""
        try:
            if self.order_index > 0:
                db = current_app.extensions['sqlalchemy']
                # Encontrar questão acima
                question_above = Question.query.filter_by(
                    quiz_id=self.quiz_id,
                    order_index=self.order_index - 1
                ).first()

                if question_above:
                    # Trocar posições
                    question_above.order_index = self.order_index
                    self.order_index = self.order_index - 1
                    db.session.commit()
                    return True

            return False
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao mover questão: {e}")
            return False

    def move_down(self):
        """Move questão para baixo na ordem"""
        try:
            db = current_app.extensions['sqlalchemy']
            # Encontrar questão abaixo
            question_below = Question.query.filter_by(
                quiz_id=self.quiz_id,
                order_index=self.order_index + 1
            ).first()

            if question_below:
                # Trocar posições
                question_below.order_index = self.order_index
                self.order_index = self.order_index + 1
                db.session.commit()
                return True

            return False
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao mover questão: {e}")
            return False

    def get_statistics_from_results(self):
        """Retorna estatísticas da questão baseadas nos resultados dos jogos"""
        # Esta função seria implementada quando tivermos um sistema
        # mais detalhado de tracking de respostas por questão

        # Por enquanto, retorna estatísticas simuladas
        return {
            'total_attempts': 0,
            'correct_answers': 0,
            'accuracy_rate': 0,
            'most_chosen_wrong_answer': None
        }

    def __repr__(self):
        preview = self.get_question_preview(50)
        return f'<Question {self.id}: {preview}>'
