"""
Rotas de Quiz - Brainchild
==========================

Responsável por:
- Criar novos quizzes com imagens
- Editar quizzes existentes
- Jogar quizzes com embaralhamento de respostas
- Gerenciar quizzes (arquivar/excluir/restaurar)
- Sistema de pontuação e resultados
"""

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models.user import User, QuizResult
from models.quiz import Quiz
from models.question import Question
from utils.decorators import admin_or_moderator_required, admin_required, quiz_owner_or_admin_required
from utils.helpers import (
    save_uploaded_file, delete_file, validate_quiz_data,
    validate_question_data, calculate_quiz_score, format_datetime
)
from datetime import datetime

# Criar blueprint para rotas de quiz
quiz = Blueprint('quiz', __name__)


@quiz.route('/create', methods=['GET', 'POST'])
@login_required
@admin_or_moderator_required
def create():
    """Criar novo quiz"""

    if request.method == 'POST':
        db = current_app.extensions['sqlalchemy']
        
        # Obter dados do formulário
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        time_limit = request.form.get('time_limit', '').strip()

        # Processar tempo limite
        time_limit_value = None
        if time_limit:
            try:
                time_limit_value = int(time_limit)
                if time_limit_value <= 0:
                    time_limit_value = None
            except ValueError:
                time_limit_value = None

        # Validar dados do quiz
        quiz_data = {
            'title': title,
            'description': description,
            'time_limit': time_limit_value
        }

        is_valid, errors = validate_quiz_data(quiz_data)

        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('quiz/create.html')

        # Processar upload de imagem
        image_filename = None
        if 'quiz_image' in request.files:
            file = request.files['quiz_image']
            if file and file.filename:
                image_filename = save_uploaded_file(file)
                if not image_filename:
                    flash('Erro ao fazer upload da imagem. Quiz criado sem imagem.', 'warning')

        # Criar quiz
        try:
            new_quiz = Quiz(
                title=title,
                description=description,
                created_by=current_user.id,
                image_filename=image_filename,
                time_limit=time_limit_value
            )

            db.session.add(new_quiz)
            db.session.commit()

            flash('Quiz criado com sucesso! Agora adicione as questões.', 'success')
            return redirect(url_for('quiz.edit', quiz_id=new_quiz.id))

        except Exception as e:
            db.session.rollback()
            if image_filename:
                delete_file(image_filename)
            flash('Erro ao criar quiz. Tente novamente.', 'error')
            print(f"Erro ao criar quiz: {e}")

    return render_template('quiz/create.html')


@quiz.route('/edit/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
@quiz_owner_or_admin_required
def edit(quiz_id):
    """Editar quiz existente"""

    quiz_obj = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
        db = current_app.extensions['sqlalchemy']
        action = request.form.get('action', 'update_quiz')

        if action == 'update_quiz':
            # Atualizar informações do quiz
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            time_limit = request.form.get('time_limit', '').strip()

            # Processar tempo limite
            time_limit_value = None
            if time_limit:
                try:
                    time_limit_value = int(time_limit)
                    if time_limit_value <= 0:
                        time_limit_value = None
                except ValueError:
                    time_limit_value = None

            # Validar dados
            quiz_data = {
                'title': title,
                'description': description,
                'time_limit': time_limit_value
            }

            is_valid, errors = validate_quiz_data(quiz_data)

            if not is_valid:
                for error in errors:
                    flash(error, 'error')
                return render_template('quiz/edit.html', quiz=quiz_obj)

            # Processar nova imagem (se enviada)
            if 'quiz_image' in request.files:
                file = request.files['quiz_image']
                if file and file.filename:
                    # Remover imagem antiga
                    if quiz_obj.image_filename:
                        delete_file(quiz_obj.image_filename)

                    # Salvar nova imagem
                    new_image = save_uploaded_file(file)
                    if new_image:
                        quiz_obj.image_filename = new_image
                    else:
                        flash('Erro ao fazer upload da nova imagem.', 'warning')

            # Atualizar quiz
            try:
                quiz_obj.title = title
                quiz_obj.description = description
                quiz_obj.time_limit = time_limit_value
                quiz_obj.updated_at = datetime.utcnow()

                db.session.commit()
                flash('Quiz atualizado com sucesso!', 'success')

            except Exception as e:
                db.session.rollback()
                flash('Erro ao atualizar quiz.', 'error')
                print(f"Erro ao atualizar quiz: {e}")

        elif action == 'add_question':
            # Adicionar nova questão
            question_text = request.form.get('question_text', '').strip()
            correct_answer = request.form.get('correct_answer', '').strip()
            option_a = request.form.get('option_a', '').strip()
            option_b = request.form.get('option_b', '').strip()
            option_c = request.form.get('option_c', '').strip()

            # Validar dados da questão
            question_data = {
                'question_text': question_text,
                'correct_answer': correct_answer,
                'option_a': option_a,
                'option_b': option_b,
                'option_c': option_c
            }

            is_valid, errors = validate_question_data(question_data)

            if not is_valid:
                for error in errors:
                    flash(error, 'error')
                return render_template('quiz/edit.html', quiz=quiz_obj)

            # Processar imagem da questão
            question_image = None
            if 'question_image' in request.files:
                file = request.files['question_image']
                if file and file.filename:
                    question_image = save_uploaded_file(file)

            # Criar questão
            try:
                next_order = len(quiz_obj.questions)

                new_question = Question(
                    quiz_id=quiz_obj.id,
                    question_text=question_text,
                    correct_answer=correct_answer,
                    option_a=option_a if option_a else None,
                    option_b=option_b if option_b else None,
                    option_c=option_c if option_c else None,
                    image_filename=question_image,
                    order_index=next_order
                )

                db.session.add(new_question)
                db.session.commit()

                flash('Questão adicionada com sucesso!', 'success')

            except Exception as e:
                db.session.rollback()
                if question_image:
                    delete_file(question_image)
                flash('Erro ao adicionar questão.', 'error')
                print(f"Erro ao adicionar questão: {e}")

    return render_template('quiz/edit.html', quiz=quiz_obj)


@quiz.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
@admin_or_moderator_required
def delete_question(question_id):
    """Excluir questão"""
    db = current_app.extensions['sqlalchemy']
    
    question = Question.query.get_or_404(question_id)
    quiz_obj = question.quiz

    # Verificar permissão
    if not (current_user.is_admin or quiz_obj.created_by == current_user.id):
        flash('Você não tem permissão para excluir esta questão.', 'error')
        return redirect(url_for('dashboard.index'))

    try:
        # Remover imagem se existir
        if question.image_filename:
            delete_file(question.image_filename)

        db.session.delete(question)
        db.session.commit()

        flash('Questão excluída com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir questão.', 'error')
        print(f"Erro ao excluir questão: {e}")

    return redirect(url_for('quiz.edit', quiz_id=quiz_obj.id))


@quiz.route('/play/<int:quiz_id>')
@login_required
def play(quiz_id):
    """Iniciar jogo do quiz"""

    quiz_obj = Quiz.query.get_or_404(quiz_id)

    # Verificar se pode ser jogado
    if not quiz_obj.can_be_played():
        flash('Este quiz não está disponível para jogar.', 'error')
        return redirect(url_for('dashboard.index'))

    # Preparar questões com respostas embaralhadas
    questions = quiz_obj.get_questions_for_play()

    if not questions:
        flash('Este quiz não possui questões.', 'warning')
        return redirect(url_for('dashboard.index'))

    # Salvar estado do jogo na sessão
    session[f'quiz_game_{quiz_id}'] = {
        'quiz_id': quiz_id,
        'questions': questions,
        'current_question': 0,
        'user_answers': [],
        'start_time': datetime.utcnow().isoformat(),
        'score': 0
    }

    return render_template('quiz/play.html',
                           quiz=quiz_obj,
                           questions=questions,
                           total_questions=len(questions))


@quiz.route('/submit_answer/<int:quiz_id>', methods=['POST'])
@login_required
def submit_answer(quiz_id):
    """Submeter resposta de uma questão"""

    game_key = f'quiz_game_{quiz_id}'

    if game_key not in session:
        return jsonify({'error': 'Jogo não encontrado'}), 404

    game_data = session[game_key]
    user_answer = request.json.get('answer', '').strip()
    question_index = request.json.get('question_index', 0)

    if question_index >= len(game_data['questions']):
        return jsonify({'error': 'Questão inválida'}), 400

    # Verificar resposta
    current_question = game_data['questions'][question_index]
    is_correct = False

    # Encontrar a alternativa selecionada
    for alternative in current_question['alternatives']:
        if alternative['letter'] == user_answer.upper():
            is_correct = alternative['is_correct']
            break

    # Salvar resposta
    game_data['user_answers'].append({
        'question_id': current_question['id'],
        'user_answer': user_answer,
        'is_correct': is_correct
    })

    if is_correct:
        game_data['score'] += 1

    game_data['current_question'] = question_index + 1
    session[game_key] = game_data

    # Verificar se é a última questão
    is_last_question = question_index >= len(game_data['questions']) - 1

    return jsonify({
        'is_correct': is_correct,
        'correct_letter': current_question['correct_letter'],
        'is_last_question': is_last_question,
        'next_question_index': question_index + 1 if not is_last_question else None
    })


@quiz.route('/finish/<int:quiz_id>', methods=['POST'])
@login_required
def finish(quiz_id):
    """Finalizar quiz e salvar resultado"""
    db = current_app.extensions['sqlalchemy']
    
    game_key = f'quiz_game_{quiz_id}'

    if game_key not in session:
        flash('Jogo não encontrado.', 'error')
        return redirect(url_for('dashboard.index'))

    game_data = session[game_key]
    quiz_obj = Quiz.query.get_or_404(quiz_id)

    # Calcular tempo gasto
    start_time = datetime.fromisoformat(game_data['start_time'])
    end_time = datetime.utcnow()
    time_spent = int((end_time - start_time).total_seconds())

    # Salvar resultado
    try:
        result = QuizResult(
            user_id=current_user.id,
            quiz_id=quiz_id,
            score=game_data['score'],
            total_questions=len(game_data['questions']),
            time_spent=time_spent
        )

        db.session.add(result)
        db.session.commit()

        # Limpar sessão
        session.pop(game_key, None)

        flash('Quiz concluído! Resultado salvo com sucesso.', 'success')
        return redirect(url_for('quiz.result', result_id=result.id))

    except Exception as e:
        db.session.rollback()
        flash('Erro ao salvar resultado.', 'error')
        print(f"Erro ao salvar resultado: {e}")
        return redirect(url_for('dashboard.index'))


@quiz.route('/result/<int:result_id>')
@login_required
def result(result_id):
    """Mostrar resultado do quiz"""

    result = QuizResult.query.get_or_404(result_id)

    # Verificar se é o dono do resultado ou admin
    if result.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para ver este resultado.', 'error')
        return redirect(url_for('dashboard.index'))

    return render_template('quiz/results.html', result=result)


@quiz.route('/manage')
@login_required
@admin_or_moderator_required
def manage():
    """Gerenciar quizzes"""

    # Filtros
    status_filter = request.args.get('status', 'all')
    created_by_filter = request.args.get('created_by', 'all')

    # Query base
    query = Quiz.query

    # Aplicar filtros
    if status_filter == 'active':
        query = query.filter_by(is_active=True, is_deleted=False, is_archived=False)
    elif status_filter == 'archived':
        query = query.filter_by(is_archived=True)
    elif status_filter == 'deleted':
        query = query.filter_by(is_deleted=True)

    # Filtro por criador (apenas para admin)
    if current_user.is_admin and created_by_filter != 'all':
        if created_by_filter == 'me':
            query = query.filter_by(created_by=current_user.id)
        else:
            try:
                creator_id = int(created_by_filter)
                query = query.filter_by(created_by=creator_id)
            except ValueError:
                pass
    elif not current_user.is_admin:
        # Moderadores só veem próprios quizzes
        query = query.filter_by(created_by=current_user.id)

    # Ordenar por data de criação
    quizzes = query.order_by(Quiz.created_at.desc()).all()

    # Lista de criadores (apenas para admin)
    creators = []
    if current_user.is_admin:
        creators = (User.query
                    .join(Quiz, User.id == Quiz.created_by)
                    .distinct()
                    .order_by(User.first_name)
                    .all())

    return render_template('quiz/manage.html',
                           quizzes=quizzes,
                           creators=creators,
                           current_status=status_filter,
                           current_creator=created_by_filter)


@quiz.route('/archive/<int:quiz_id>', methods=['POST'])
@login_required
@admin_or_moderator_required
def archive(quiz_id):
    """Arquivar quiz"""

    quiz_obj = Quiz.query.get_or_404(quiz_id)

    # Verificar permissão
    if not (current_user.is_admin or quiz_obj.created_by == current_user.id):
        flash('Você não tem permissão para arquivar este quiz.', 'error')
        return redirect(url_for('quiz.manage'))

    try:
        quiz_obj.archive()
        flash('Quiz arquivado com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao arquivar quiz.', 'error')
        print(f"Erro ao arquivar quiz: {e}")

    return redirect(url_for('quiz.manage'))


@quiz.route('/delete/<int:quiz_id>', methods=['POST'])
@login_required
def delete(quiz_id):
    """Excluir quiz (apenas admin)"""

    quiz_obj = Quiz.query.get_or_404(quiz_id)

    # Apenas admin pode excluir
    if not current_user.is_admin:
        flash('Apenas administradores podem excluir quizzes.', 'error')
        return redirect(url_for('quiz.manage'))

    try:
        quiz_obj.delete()
        flash('Quiz excluído com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao excluir quiz.', 'error')
        print(f"Erro ao excluir quiz: {e}")

    return redirect(url_for('quiz.manage'))


@quiz.route('/restore/<int:quiz_id>', methods=['POST'])
@login_required
def restore(quiz_id):
    """Restaurar quiz arquivado/excluído (apenas admin)"""

    quiz_obj = Quiz.query.get_or_404(quiz_id)

    # Apenas admin pode restaurar
    if not current_user.is_admin:
        flash('Apenas administradores podem restaurar quizzes.', 'error')
        return redirect(url_for('quiz.manage'))

    try:
        quiz_obj.restore()
        flash('Quiz restaurado com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao restaurar quiz.', 'error')
        print(f"Erro ao restaurar quiz: {e}")

    return redirect(url_for('quiz.manage'))


@quiz.route('/view/<int:quiz_id>')
@login_required
def view(quiz_id):
    """Visualizar detalhes do quiz"""

    quiz_obj = Quiz.query.get_or_404(quiz_id)

    # Verificar se pode visualizar
    if not (quiz_obj.can_be_played() or
            current_user.is_admin or
            quiz_obj.created_by == current_user.id):
        flash('Você não tem permissão para visualizar este quiz.', 'error')
        return redirect(url_for('dashboard.index'))

    # Estatísticas do quiz
    stats = quiz_obj.get_completion_stats()

    # Resultados recentes (se for criador ou admin)
    recent_results = []
    if current_user.is_admin or quiz_obj.created_by == current_user.id:
        recent_results = quiz_obj.get_recent_results(10)

    return render_template('quiz/view.html',
                           quiz=quiz_obj,
                           stats=stats,
                           recent_results=recent_results)
