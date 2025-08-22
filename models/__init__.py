"""
Modelos do Banco de Dados - Brainchild
=====================================

Este módulo contém todos os modelos (estruturas) do banco de dados:
- User: Usuários do sistema (Admin, Moderador, Aluno)
- Quiz: Quizzes criados pelos usuários
- Question: Questões dos quizzes
- QuizResult: Resultados dos quizzes jogados
"""

from .user import User, QuizResult
from .quiz import Quiz
from .question import Question

# Lista de todos os modelos disponíveis para import
__all__ = [
    'User',
    'Quiz',
    'Question',
    'QuizResult'
]

# Versão do módulo
__version__ = '1.0.0'