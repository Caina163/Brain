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
    
    if request.method == 'GET':
        return render_template('quiz/create.html')
    
    try:
        db = current_app.extensions['sqlalchemy']
        print("=== DEBUG: Iniciando criação de quiz ===")
        
        # Pegar dados básicos do formulário
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        questions_json = request.form.get('questions_data', '')
        
        print(f"DEBUG: title='{title}'")
        print(f"DEBUG: description='{description}'")
        print(f"DEBUG: questions_json presente: {bool(questions_json)}")
        
        # Validar título obrigatório
        if not title:
            print("DEBUG: Erro - título vazio")
            flash('Título é obrigatório.', 'error')
            return render_template('quiz/create.html')
        
        if not questions_json:
            print("DEBUG: Erro - nenhuma questão fornecida")
            flash('Adicione pelo menos uma questão ao quiz.', 'error')
            return render_template('quiz/create.html')
        
        # Parse das questões
        try:
            questions_data = json.loads(questions_json)
            print(f"DEBUG: questions_data parsed: {len(questions_data)} questões")
            
            # Debug: mostrar estrutura das questões
            for i, q in enumerate(questions_data):
                print(f"DEBUG: Questão {i+1}: question='{q.get('question', '')[:50]}...', answers={len(q.get('answers', []))}")
                
        except json.JSONDecodeError as e:
            print(f"DEBUG: Erro JSON decode: {e}")
            flash('Erro no formato das questões.', 'error')
            return render_template('quiz/create.html')
        
        # Validar questões básica
        valid_questions = []
        for i, question_data in enumerate(questions_data):
            question_text = question_data.get('question', '').strip()
            answers = question_data.get('answers', [])
            
            if not question_text:
                print(f"DEBUG: Questão {i+1} sem texto")
                continue
                
            if len(answers) < 2:
                print(f"DEBUG: Questão {i+1} precisa de pelo menos 2 respostas")
                continue
                
            # Verificar se tem resposta correta
            has_correct = any(answer.get('isCorrect', False) for answer in answers)
            if not has_correct:
                print(f"DEBUG: Questão {i+1} sem resposta correta")
                continue
                
            valid_questions.append(question_data)
            print(f"DEBUG: Questão {i+1} válida")
        
        if not valid_questions:
            print("DEBUG: Nenhuma questão válida encontrada")
            flash('Nenhuma questão válida encontrada.', 'error')
            return render_template('quiz/create.html')
        
        print(f"DEBUG: {len(valid_questions)} questões válidas processadas")
        
        # Processar imagem do quiz
        image_filename = None
        if 'quiz_image' in request.files:
            file = request.files['quiz_image']
            if file and file.filename:
                print("DEBUG: Processando imagem do quiz")
                image_filename = save_uploaded_file(file)
                if not image_filename:
                    print("DEBUG: Erro ao salvar imagem do quiz")
                    flash('Erro ao fazer upload da imagem.', 'warning')
        
        print("DEBUG: Criando objeto Quiz...")
        
        # Criar quiz
        new_quiz = Quiz(
            title=title,
            description=description if description else None,
            created_by=current_user.id,
            image_filename=image_filename
        )
        
        print("DEBUG: Adicionando quiz à sessão do banco...")
        db.session.add(new_quiz)
        db.session.flush()  # Para obter o ID
        
        print(f"DEBUG: Quiz criado com ID: {new_quiz.id}")
        
        # Processar cada questão válida
        for i, question_data in enumerate(valid_questions):
            print(f"DEBUG: Processando questão {i+1} de {len(valid_questions)}")
            
            question_text = question_data.get('question', '').strip()
            answers = question_data.get('answers', [])
            
            # Separar resposta correta das incorretas
            correct_answer = None
            wrong_answers = []
            
            for answer in answers:
                answer_text = answer.get('text', '').strip()
                is_correct = answer.get('isCorrect', False)
                
                if not answer_text:
                    continue
                    
                if is_correct and not correct_answer:
                    correct_answer = answer_text
                    print(f"DEBUG: Resposta correta: {answer_text[:30]}...")
                elif not is_correct:
                    wrong_answers.append(answer_text)
                    print(f"DEBUG: Resposta incorreta: {answer_text[:30]}...")
            
            if not correct_answer:
                print(f"DEBUG: ERRO - Questão {i+1} sem resposta correta válida")
                continue
            
            # Criar questão no formato do modelo existente
            new_question = Question(
                quiz_id=new_quiz.id,
                question_text=question_text,
                correct_answer=correct_answer,
                option_a=wrong_answers[0] if len(wrong_answers) > 0 else None,
                option_b=wrong_answers[1] if len(wrong_answers) > 1 else None,
                option_c=wrong_answers[2] if len(wrong_answers) > 2 else None,
                order_index=i
            )
            
            db.session.add(new_question)
            print(f"DEBUG: Questão {i+1} adicionada: {len(wrong_answers)} alternativas incorretas")
        
        # COMMIT FINAL - CRUCIAL PARA SALVAR
        print("DEBUG: Fazendo commit final...")
        db.session.commit()
        print("DEBUG: ✅ Quiz e questões salvos com SUCESSO!")
        
        flash('Quiz criado com sucesso!', 'success')
        return redirect(url_for('dashboard.index'))
        
    except Exception as e:
        print(f"DEBUG: 💥 ERRO COMPLETO: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Rollback em caso de erro
        try:
            db.session.rollback()
            print("DEBUG: Rollback realizado")
        except:
            pass
            
        flash(f'Erro ao criar quiz: {str(e)}', 'error')
        return render_template('quiz/create.html')


@quiz.route('/edit/<int:quiz_id>', methods=['GET', 'POST'])
@login_required  
@quiz_owner_or_admin_required
def edit(quiz_id):
    """Editar quiz existente"""
    quiz_obj = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        db = current_app.extensions['sqlalchemy']
        
        # Atualizar informações básicas
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title:
            flash('Título é obrigatório', 'error')
            return render_template('quiz/edit.html', quiz=quiz_obj)
        
        try:
            quiz_obj.title = title
            quiz_obj.description = description
            quiz_obj.updated_at = datetime.utcnow()
            
            # Processar nova imagem se enviada
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
                        flash('Erro ao fazer upload da imagem.', 'warning')
            
            db.session.commit()
            flash('Quiz atualizado com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar quiz.', 'error')
            print(f"Erro ao atualizar quiz: {e}")
    
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


@quiz.route('/manage')
@login_required
@admin_or_moderator_required
def manage():
    """Gerenciar quizzes"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'active')
    search = request.args.get('search', '')
    
    # Query base - quizzes do usuário atual
    query = Quiz.query.filter_by(created_by=current_user.id)
    
    # Aplicar filtros de status usando campos corretos
    if status_filter == 'active':
        query = query.filter_by(is_active=True, is_deleted=False, is_archived=False)
    elif status_filter == 'archived':
        query = query.filter_by(is_archived=True)
    elif status_filter == 'deleted':
        query = query.filter_by(is_deleted=True)
    
    # Aplicar busca por título
    if search:
        query = query.filter(Quiz.title.ilike(f'%{search}%'))
    
    # Ordenar por data de criação
    query = query.order_by(Quiz.created_at.desc())
    
    # Paginação
    try:
        quizzes = query.paginate(
            page=page,
            per_page=10,
            error_out=False
        )
    except Exception as e:
        print(f"Erro na paginação: {e}")
        quizzes = query.limit(10).all()
    
    return render_template('quiz/manage.html',
                          quizzes=quizzes,
                          current_status=status_filter,
                          search_term=search)


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
        db = current_app.extensions['sqlalchemy']
        quiz_obj.is_archived = True
        quiz_obj.is_active = False
        quiz_obj.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Quiz arquivado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao arquivar quiz.', 'error')
        print(f"Erro ao arquivar quiz: {e}")
    
    return redirect(url_for('quiz.manage'))


@quiz.route('/delete/<int:quiz_id>', methods=['POST'])
@login_required
def delete(quiz_id):
    """Excluir quiz (soft delete)"""
    quiz_obj = Quiz.query.get_or_404(quiz_id)
    
    try:
        db = current_app.extensions['sqlalchemy']
        quiz_obj.is_deleted = True
        quiz_obj.is_active = False
        quiz_obj.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Quiz excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir quiz.', 'error')
        print(f"Erro ao excluir quiz: {e}")
    
    return redirect(url_for('quiz.manage'))


@quiz.route('/restore/<int:quiz_id>', methods=['POST'])
@login_required
def restore(quiz_id):
    """Restaurar quiz arquivado/excluído"""
    quiz_obj = Quiz.query.get_or_404(quiz_id)
    
    # Apenas admin pode restaurar
    if not current_user.is_admin:
        flash('Apenas administradores podem restaurar quizzes.', 'error')
        return redirect(url_for('quiz.manage'))
    
    try:
        db = current_app.extensions['sqlalchemy']
        quiz_obj.is_deleted = False
        quiz_obj.is_archived = False
        quiz_obj.is_active = True
        quiz_obj.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Quiz restaurado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
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
        try:
            recent_results = QuizResult.query.filter_by(quiz_id=quiz_id).order_by(QuizResult.completed_at.desc()).limit(10).all()
        except:
            recent_results = []
    
    return render_template('quiz/view.html',
                          quiz=quiz_obj,
                          stats=stats,
                          recent_results=recent_results)


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
