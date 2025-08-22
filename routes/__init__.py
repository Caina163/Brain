"""
Rotas do Sistema Brainchild
===========================
Este módulo contém todas as rotas organizadas por funcionalidade:
- auth: Autenticação (login, registro, logout)
- dashboard: Páginas principais por tipo de usuário
- quiz: Criar, editar, jogar e gerenciar quizzes
- user: Perfil e gerenciamento de usuários
"""
from .auth import auth
from .dashboard import dashboard
from .quiz import quiz
from .user import user

# Lista de todos os blueprints disponíveis
__all__ = [
    'auth',
    'dashboard',
    'quiz',
    'user'
]

# Versão do módulo
__version__ = '1.0.0'
