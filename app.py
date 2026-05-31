# Project: AI Job Interview Coach
# Author: Imtiaz Adar
# Contact: imtiazadarofficial@gmail.com

import streamlit as st
import os
import tempfile
import re
import json
import time
import random

from google import genai
from google.genai import types
from gtts import gTTS
import speech_recognition as sr
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ----------------------------------
# PAGE CONFIG
# ----------------------------------
st.set_page_config(
    page_title="AI Job Interview Coach",
    page_icon="mentoring.png",
    layout="wide"
)

# ----------------------------------
# GEMINI CLIENT
# ----------------------------------
@st.cache_resource
def get_gemini_client():
    """Initialize Gemini client with API key from environment"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY not found in environment variables!")
        st.stop()
    return genai.Client(api_key=api_key)

client = get_gemini_client()

# Model configuration
GEMINI_MODEL = "gemini-2.0-flash"

# ----------------------------------
# CUSTOM CSS
# ----------------------------------
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .feedback-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .role-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        color: white;
        font-weight: bold;
    }
    .question-card {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------
# TITLE SECTION
# ----------------------------------
st.markdown("""
<div class="main-header">
    <h1 style='color:white; margin:0;'>AI Job Interview Coach</h1>
    <p style='color:white; margin-top:10px;'>Master your interview skills with AI-powered feedback</p>
    <hr style='background-color:white;'>
    <p style='color:white; margin:0;'>Built by <strong>Imtiaz Adar</strong></p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------
# SESSION STATE
# ----------------------------------
def init_session_state():
    defaults = {
        "interview_active": False,
        "interview_complete": False,
        "questions": [],
        "answers": [],
        "current_question_index": 0,
        "final_feedback": None,
        "summary_audio": None,
        "question_scores": [],
        "overall_score": 0,
        "current_role": "",
        "evaluation_error": None,
        "metrics": {
            "Communication": 0,
            "Confidence": 0,
            "Relevance": 0,
            "Problem Solving": 0,
            "Professionalism": 0
        },
        "api_call_count": 0,
        "last_api_call": 0
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ----------------------------------
# API MANAGEMENT
# ----------------------------------
def check_api_quota():
    current_time = time.time()
    if current_time - st.session_state.last_api_call < 1:
        time.sleep(0.5)
    st.session_state.last_api_call = current_time
    st.session_state.api_call_count += 1
    
    if st.session_state.api_call_count > 50:
        st.warning("⚠️ Approaching API quota limit.")
        return False
    return True

# ----------------------------------
# AUDIO FUNCTIONS
# ----------------------------------
def generate_audio_summary(text):
    if not text or len(text.strip()) < 10:
        return None
        
    try:
        if len(text) > 2000:
            text = text[:2000] + "..."
            
        tts = gTTS(text, lang='en', slow=False)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        st.warning(f"Audio generation failed: {str(e)[:100]}")
        return None

def speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_file.getbuffer())
            temp_path = f.name
        
        with sr.AudioFile(temp_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        
        text = recognizer.recognize_google(audio_data)
        
        try:
            os.unlink(temp_path)
        except:
            pass
            
        return text.strip()
        
    except sr.UnknownValueError:
        st.warning("Could not understand the audio. Please speak clearly.")
        return None
    except Exception as e:
        st.warning(f"Error processing audio: {str(e)[:100]}")
        return None

# ----------------------------------
# ULTRA DYNAMIC QUESTION GENERATION - FIXED!
# ----------------------------------
def generate_questions(role):
    """Generate UNIQUE, DYNAMIC interview questions using Gemini - ALWAYS fresh!"""
    
    role_clean = role.strip().title()
    
    # Different question styles to rotate for variety
    question_styles = [
        "technical and behavioral",
        "situational and problem-solving",
        "experience-based and future-oriented",
        "skills-focused and culture-fit",
        "challenge-based and growth-oriented"
    ]
    
    # Pick a random style for variety
    selected_style = random.choice(question_styles)
    
    # Enhanced prompt for maximum variety
    prompt = f"""You are a professional interviewer creating a UNIQUE interview for a {role_clean} position.

IMPORTANT: Create FRESH, DIFFERENT questions each time. Never repeat the same questions.

Generate 5 interview questions that are:
- {selected_style}
- SPECIFIC to {role_clean} (not generic)
- Realistic for an actual interview
- Challenging but fair
- Different from typical questions

Question types to include (mix them):
1. One about motivation/passion for {role_clean}
2. One about technical/skills relevant to {role_clean}
3. One about handling challenges/setbacks
4. One about teamwork/collaboration
5. One about future goals/aspirations

Return ONLY the 5 questions, one per line.
No numbering, no explanations, no extra text.

Questions:"""

    try:
        # Call Gemini with HIGH temperature for creativity
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9,  # High temperature for variety
                max_output_tokens=800,
                top_p=0.95,  # More diverse token selection
                top_k=40
            )
        )
        
        # Parse questions
        questions = [q.strip() for q in response.text.split('\n') if q.strip()]
        
        # Clean up any numbering
        questions = [re.sub(r'^\d+\.\s*', '', q) for q in questions]
        questions = [re.sub(r'^[Qq]\d+[:.)]\s*', '', q) for q in questions]
        
        # Ensure exactly 5 questions
        if len(questions) > 5:
            questions = questions[:5]
        elif len(questions) < 5:
            # Generate missing questions with a fallback call
            missing_count = 5 - len(questions)
            fallback_prompt = f"Generate {missing_count} more unique interview questions for a {role_clean} position. One per line:"
            
            try:
                fallback_response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=fallback_prompt,
                    config=types.GenerateContentConfig(temperature=0.85, max_output_tokens=400)
                )
                fallback_qs = [q.strip() for q in fallback_response.text.split('\n') if q.strip()]
                questions.extend(fallback_qs[:missing_count])
            except:
                # Ultimate fallback - dynamic role-based questions
                questions.extend(get_emergency_questions(role, missing_count))
        
        # Verify questions are role-appropriate
        if questions and len(questions) == 5:
            return questions
        else:
            return get_emergency_questions(role, 5)
        
    except Exception as e:
        st.warning(f"⚠️ API issue: {str(e)[:100]}. Generating fresh questions anyway...")
        return get_emergency_questions(role, 5)

def get_emergency_questions(role, count):
    """Dynamic emergency questions - never static, always role-based"""
    role_lower = role.lower()
    questions = []
    
    # Question templates that get customized
    templates = [
        f"What excites you most about the {role} role and why?",
        f"Describe a challenging situation you faced that relates to {role} work.",
        f"What skills make someone successful as a {role}?",
        f"How would you handle a disagreement with a colleague about {role} responsibilities?",
        f"Where do you see your {role} career in 3 years?"
    ]
    
    # Role-specific customizations
    if any(tech in role_lower for tech in ['engineer', 'developer', 'programmer', 'software']):
        templates = [
            f"What's the most interesting technical problem you've solved as a {role}?",
            f"How do you stay current with {role} technologies and best practices?",
            f"Describe your approach to debugging a complex {role} issue.",
            f"What's your favorite programming language/tool for {role} work and why?",
            f"How do you balance perfect code with shipping deadlines as a {role}?"
        ]
    elif any(creative in role_lower for creative in ['animator', 'designer', 'artist', 'creative']):
        templates = [
            f"What inspires your {role} creative process?",
            f"Describe a {role} project you're most proud of and why.",
            f"How do you handle creative blocks in your {role} work?",
            f"What {role} tools/software do you prefer and what would you improve?",
            f"How do you incorporate feedback into your {role} creative work?"
        ]
    elif any(marketing in role_lower for marketing in ['marketing', 'sales', 'business']):
        templates = [
            f"What's your {role} approach to understanding customer needs?",
            f"Describe a successful {role} campaign/project you worked on.",
            f"How do you measure {role} success and what metrics matter most?",
            f"What's your {role} strategy for reaching new audiences?",
            f"How do you handle {role} rejection or a failed initiative?"
        ]
    
    # Add variety with random selection
    random.shuffle(templates)
    return templates[:count]

# ----------------------------------
# ENHANCED HEURISTIC SCORING
# ----------------------------------
def calculate_heuristic_scores(questions, answers, role):
    """Calculate scores based on answer quality"""
    question_scores = []
    
    for answer in answers:
        score = 5
        
        if not answer or len(answer.strip()) < 10:
            score = 2
        else:
            if len(answer) > 50:
                score += 1
            if len(answer) > 150:
                score += 1
            if len(answer) > 300:
                score += 1
            
            quality_words = ['because', 'example', 'experience', 'learned', 'implemented', 
                           'developed', 'achieved', 'result', 'project', 'team', 'responsible',
                           'created', 'designed', 'built', 'solved', 'improved', 'specific']
            for word in quality_words:
                if word in answer.lower():
                    score += 0.3
            
            if re.search(r'(first|second|third|finally|additionally|moreover|specifically)', answer.lower()):
                score += 0.5
            
            role_lower = role.lower()
            # Role-specific keyword matching
            role_keywords = {
                'animator': ['animate', 'motion', 'keyframe', 'character', 'storyboard', 'illustration'],
                'designer': ['design', 'creative', 'interface', 'prototype', 'visual', 'figma'],
                'engineer': ['code', 'programming', 'debug', 'function', 'system', 'architecture', 'python'],
                'marketing': ['campaign', 'audience', 'engagement', 'analytics', 'strategy', 'brand'],
                'sales': ['customer', 'client', 'revenue', 'target', 'negotiation', 'relationship']
            }
            
            for category, keywords in role_keywords.items():
                if category in role_lower:
                    for keyword in keywords:
                        if keyword in answer.lower():
                            score += 0.5
                    break
        
        question_scores.append(min(10, int(score)))
    
    all_answers = " ".join(answers)
    avg_score = sum(question_scores) / len(question_scores)
    
    metrics = {
        "Communication": min(10, int(avg_score) + 1),
        "Confidence": min(10, min(8, int(len(all_answers) / 100) + 5)),
        "Relevance": min(10, int(avg_score)),
        "Problem Solving": min(10, question_scores[2] if len(question_scores) > 2 else int(avg_score)),
        "Professionalism": min(10, 7 + (1 if len(answers) >= 4 else 0) + (1 if 'thank' in all_answers.lower() else 0))
    }
    
    overall_score = sum(question_scores) // len(question_scores)
    
    return question_scores, overall_score, metrics

# ----------------------------------
# GENERATE FEEDBACK WITHOUT API
# ----------------------------------
def generate_fallback_feedback(questions, answers, role, scores, metrics):
    """Generate detailed feedback without API"""
    
    feedback = f"## 🎯 Interview Feedback for {role} Position\n\n"
    
    if metrics['Communication'] >= 8:
        feedback += "**Overall Assessment:** 🌟 Excellent performance! You demonstrated strong communication skills and relevant knowledge.\n\n"
    elif metrics['Communication'] >= 6:
        feedback += "**Overall Assessment:** 👍 Good performance with room for improvement. Your answers showed potential.\n\n"
    else:
        feedback += "**Overall Assessment:** 📈 Needs improvement. Focus on providing more detailed and structured answers.\n\n"
    
    feedback += "### 💪 Strengths:\n"
    strengths = []
    if metrics['Communication'] >= 7:
        strengths.append("- ✅ Good communication skills demonstrated")
    if metrics['Confidence'] >= 7:
        strengths.append("- ✅ Shows confidence in responses")
    if max(len(a) for a in answers) > 200:
        strengths.append("- ✅ Provides detailed, thoughtful answers")
    if any('project' in a.lower() for a in answers):
        strengths.append("- ✅ References practical experience")
    if any('example' in a.lower() for a in answers):
        strengths.append("- ✅ Uses concrete examples effectively")
    
    feedback += "\n".join(strengths) if strengths else "- Good effort on completing the interview\n"
    feedback += "\n\n"
    
    feedback += "### 📈 Areas for Improvement:\n"
    improvements = []
    if any(len(a) < 50 for a in answers):
        improvements.append("- 📝 Provide more detailed answers (aim for 2-3 sentences minimum)")
    if metrics['Problem Solving'] < 7:
        improvements.append("- 🧠 Work on structuring problem-solving approaches (use STAR method)")
    if not any('example' in a.lower() for a in answers):
        improvements.append("- 💡 Include specific examples from your experience")
    if not any('because' in a.lower() for a in answers):
        improvements.append("- 🔍 Explain your reasoning more thoroughly")
    
    feedback += "\n".join(improvements) if improvements else "- Continue practicing to refine your skills\n"
    feedback += "\n\n"
    
    feedback += "### 🎯 Specific Recommendations:\n"
    feedback += f"1. 🔬 **Research:** Deeply understand the {role} role and company culture\n"
    feedback += "2. 📋 **Structure:** Use STAR (Situation, Task, Action, Result) for behavioral questions\n"
    feedback += "3. 📚 **Prepare:** Have 3-4 detailed examples ready from your experience\n"
    feedback += "4. 🎤 **Practice:** Record yourself answering common interview questions\n"
    
    return feedback

# ----------------------------------
# EVALUATE INTERVIEW
# ----------------------------------
def evaluate_interview(questions, answers, role):
    """Evaluate interview using Gemini"""
    if not check_api_quota():
        return None, "API quota exceeded. Using heuristic evaluation."
    
    qa_pairs = []
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        qa_pairs.append(f"Q{i}: {q}\nA{i}: {a}\n")
    
    prompt = f"""You are an expert interview coach evaluating a candidate for a {role} position.

Interview Transcript:
{''.join(qa_pairs)}

Provide evaluation in EXACTLY this format:

OVERALL_SCORE: [number 1-10]

COMMUNICATION: [number 1-10]
CONFIDENCE: [number 1-10]
RELEVANCE: [number 1-10]
PROBLEM_SOLVING: [number 1-10]
PROFESSIONALISM: [number 1-10]

QUESTION_SCORES: [number], [number], [number], [number], [number]

STRENGTHS:
- strength 1
- strength 2
- strength 3

IMPROVEMENTS:
- improvement 1
- improvement 2
- improvement 3

FEEDBACK: [3-4 sentences of specific advice]

RECOMMENDATION: [Strong Hire/Hire/Consider/Needs Improvement]"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1500
            )
        )
        return response.text, None
        
    except Exception as e:
        return None, str(e)

# ----------------------------------
# EXTRACT SCORES
# ----------------------------------
def extract_scores(evaluation_text):
    """Extract numerical scores from evaluation text"""
    
    question_scores = [7, 7, 7, 7, 7]
    overall_score = 7
    metrics = {
        "Communication": 7,
        "Confidence": 7,
        "Relevance": 7,
        "Problem Solving": 7,
        "Professionalism": 7
    }
    
    if not evaluation_text:
        return question_scores, overall_score, metrics
    
    scores_match = re.search(r'QUESTION_SCORES:\s*([\d,\s]+)', evaluation_text, re.IGNORECASE)
    if scores_match:
        scores_text = scores_match.group(1)
        found_scores = re.findall(r'(\d+)', scores_text)
        if len(found_scores) >= 5:
            question_scores = [min(10, max(1, int(s))) for s in found_scores[:5]]
    
    overall_match = re.search(r'OVERALL_SCORE:\s*(\d+)', evaluation_text, re.IGNORECASE)
    if overall_match:
        overall_score = min(10, max(1, int(overall_match.group(1))))
    
    for metric in metrics.keys():
        match = re.search(rf'{metric}:\s*(\d+)', evaluation_text, re.IGNORECASE)
        if match:
            metrics[metric] = min(10, max(1, int(match.group(1))))
    
    return question_scores, overall_score, metrics

# ----------------------------------
# BUILD DASHBOARD
# ----------------------------------
def build_dashboard(question_scores, metrics):
    """Create visual dashboard with charts"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Question Performance")
        df_questions = pd.DataFrame({
            "Question": [f"Q{i+1}" for i in range(5)],
            "Score": question_scores
        })
        
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        colors = ['#4CAF50' if s >= 7 else '#FF9800' if s >= 5 else '#F44336' for s in question_scores]
        bars = ax1.bar(df_questions["Question"], df_questions["Score"], color=colors)
        ax1.set_ylim(0, 10)
        ax1.set_ylabel("Score")
        ax1.set_title("Score per Question", fontsize=14, fontweight='bold')
        ax1.axhline(y=7, color='green', linestyle='--', alpha=0.5, label='Good (7+)')
        ax1.axhline(y=5, color='orange', linestyle='--', alpha=0.5, label='Pass (5+)')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        for bar, score in zip(bars, question_scores):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{score}', ha='center', va='bottom', fontweight='bold')
        
        st.pyplot(fig1)
        plt.close()
    
    with col2:
        st.markdown("### 🎯 Skill Assessment")
        df_metrics = pd.DataFrame({
            "Skill": list(metrics.keys()),
            "Score": list(metrics.values())
        })
        
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        colors = ['#4CAF50' if s >= 7 else '#FF9800' if s >= 5 else '#F44336' for s in metrics.values()]
        bars = ax2.barh(df_metrics["Skill"], df_metrics["Score"], color=colors)
        ax2.set_xlim(0, 10)
        ax2.set_xlabel("Score")
        ax2.set_title("Skills Breakdown", fontsize=14, fontweight='bold')
        ax2.axvline(x=7, color='green', linestyle='--', alpha=0.5, label='Good')
        ax2.axvline(x=5, color='orange', linestyle='--', alpha=0.5, label='Pass')
        ax2.legend()
        
        for bar, score in zip(bars, metrics.values()):
            ax2.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                    f'{score}', va='center', fontweight='bold')
        
        st.pyplot(fig2)
        plt.close()

# ----------------------------------
# RESET INTERVIEW
# ----------------------------------
def reset_interview():
    st.session_state.interview_active = False
    st.session_state.interview_complete = False
    st.session_state.questions = []
    st.session_state.answers = []
    st.session_state.current_question_index = 0
    st.session_state.final_feedback = None
    st.session_state.summary_audio = None
    st.session_state.question_scores = []
    st.session_state.overall_score = 0
    st.session_state.current_role = ""
    st.session_state.evaluation_error = None
    st.session_state.metrics = {
        "Communication": 0,
        "Confidence": 0,
        "Relevance": 0,
        "Problem Solving": 0,
        "Professionalism": 0
    }

# ----------------------------------
# SIDEBAR
# ----------------------------------
with st.sidebar:
    st.markdown("## 🎮 Interview Setup")
    
    role = st.text_input("💼 Job Role", 
                        placeholder="e.g., Animator, Software Engineer, Marketing Manager",
                        key="role_input_field")
    
    if role_audio := st.audio_input("🎤 Speak Role", key="role_audio_input"):
        if detected_role := speech_to_text(role_audio):
            role = detected_role
            st.success(f"✅ Detected: {role}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_clicked = st.button("🚀 Start Interview", type="primary", use_container_width=True, key="start_button")
    
    with col2:
        reset_clicked = st.button("🔄 Reset", use_container_width=True, key="reset_button")
    
    if start_clicked and role:
        st.session_state.current_role = role
        with st.spinner(f"🎯 Generating UNIQUE {role} interview questions..."):
            st.session_state.questions = generate_questions(role)
            if st.session_state.questions and len(st.session_state.questions) == 5:
                st.success(f"✅ Generated {len(st.session_state.questions)} fresh questions!")
                st.session_state.interview_active = True
                st.session_state.interview_complete = False
                st.session_state.current_question_index = 0
                st.session_state.answers = []
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to generate questions. Please try again.")
    elif start_clicked and not role:
        st.warning("⚠️ Please enter a job role first!")
    
    if reset_clicked:
        reset_interview()
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🎲 Dynamic Questions")
    st.markdown("""
    ✨ Each interview generates **UNIQUE** questions
    ✨ Questions are tailored to your specific role
    ✨ Never the same interview twice!
    """)

# ----------------------------------
# MAIN INTERVIEW FLOW
# ----------------------------------
if st.session_state.interview_active and not st.session_state.interview_complete:
    
    st.markdown(f"""
    <div style='text-align: center; margin-bottom: 20px;'>
        <span class='role-badge'>🎯 Interviewing for: {st.session_state.current_role}</span>
    </div>
    """, unsafe_allow_html=True)
    
    total_questions = len(st.session_state.questions)
    current_q = st.session_state.current_question_index
    
    if current_q < total_questions:
        
        st.progress(current_q / total_questions, text=f"Question {current_q + 1} of {total_questions}")
        
        question = st.session_state.questions[current_q]
        
        st.markdown(f"""
        <div class="question-card">
            <h3 style='color: #667eea; margin-top: 0;'>📌 Question {current_q + 1}</h3>
            <p style='font-size: 1.1rem; line-height: 1.5; margin-bottom: 0;'>{question}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            text_answer = st.text_area(
                "✍️ Type your answer",
                height=150,
                placeholder="Type your response here...",
                key=f"text_answer_{current_q}"
            )
        
        with col2:
            st.markdown("### 🎤 Or speak your answer")
            audio_key = f"audio_answer_{current_q}"
            if audio_answer := st.audio_input("Click to record", key=audio_key):
                with st.spinner("🎙️ Processing your speech..."):
                    if spoken_text := speech_to_text(audio_answer):
                        st.success("✅ Voice captured successfully!")
                        st.info(f"📝 Transcribed: {spoken_text}")
                        text_answer = spoken_text
        
        submit_key = f"submit_button_{current_q}"
        if st.button("📤 Submit Answer", type="primary", use_container_width=True, key=submit_key):
            if text_answer and text_answer.strip():
                st.session_state.answers.append(text_answer.strip())
                st.session_state.current_question_index += 1
                st.success("✅ Answer submitted! Moving to next question...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("⚠️ Please provide an answer before submitting")
    
    else:
        st.session_state.interview_complete = True
        st.session_state.interview_active = False
        
        with st.spinner("🤖 AI is analyzing your interview performance..."):
            evaluation, error = evaluate_interview(
                st.session_state.questions,
                st.session_state.answers,
                st.session_state.current_role
            )
            
            if evaluation and not error:
                q_scores, overall, metrics = extract_scores(evaluation)
                st.session_state.final_feedback = evaluation
                st.session_state.question_scores = q_scores
                st.session_state.overall_score = overall
                st.session_state.metrics = metrics
                st.session_state.evaluation_error = None
                st.success("✅ Evaluation complete!")
            else:
                st.info(f"📊 Using intelligent scoring system")
                q_scores, overall, metrics = calculate_heuristic_scores(
                    st.session_state.questions,
                    st.session_state.answers,
                    st.session_state.current_role
                )
                st.session_state.final_feedback = generate_fallback_feedback(
                    st.session_state.questions,
                    st.session_state.answers,
                    st.session_state.current_role,
                    q_scores,
                    metrics
                )
                st.session_state.question_scores = q_scores
                st.session_state.overall_score = overall
                st.session_state.metrics = metrics
                st.session_state.evaluation_error = "Using intelligent scoring"
            
            summary_text = f"{st.session_state.current_role} interview complete. Overall score: {st.session_state.overall_score} out of 10."
            st.session_state.summary_audio = generate_audio_summary(summary_text)
        
        st.rerun()

# ----------------------------------
# RESULTS DISPLAY
# ----------------------------------
elif st.session_state.interview_complete:
    
    st.balloons()
    st.markdown(f"## 🎉 {st.session_state.current_role} Interview Complete!")
    
    if st.session_state.evaluation_error:
        st.info(f"ℹ️ {st.session_state.evaluation_error}")
    
    st.markdown(f"""
    <div class="score-card">
        <h2 style='margin:0;'>🎯 Overall Score</h2>
        <h1 style='font-size: 4rem; margin:10px 0;'>{st.session_state.overall_score}<span style='font-size: 2rem;'>/10</span></h1>
        <p style='margin:0;'>{st.session_state.current_role}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## 📊 Performance Metrics")
    cols = st.columns(5)
    for col, (metric, score) in zip(cols, st.session_state.metrics.items()):
        with col:
            color = "#4CAF50" if score >= 7 else "#FF9800" if score >= 5 else "#F44336"
            st.markdown(f"""
            <div class="metric-card">
                <p style='margin:0; color:#666; font-size:0.9rem;'>{metric}</p>
                <h2 style='margin:5px 0; color:{color};'>{score}</h2>
                <p style='margin:0; font-size:0.8rem; color:#888;'>/10</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    build_dashboard(st.session_state.question_scores, st.session_state.metrics)
    
    st.markdown("---")
    
    st.markdown("## 📝 Detailed Analysis")
    with st.expander("🔍 View Full Feedback", expanded=True):
        st.markdown(st.session_state.final_feedback)
    
    if st.session_state.summary_audio:
        st.markdown("## 🔊 Audio Summary")
        st.audio(st.session_state.summary_audio)
    
    st.markdown("---")
    
    st.markdown("## 📋 Interview Transcript")
    for idx, (q, a) in enumerate(zip(st.session_state.questions, st.session_state.answers)):
        with st.expander(f"Q{idx+1}: {q[:100]}..."):
            st.markdown(f"**Question:** {q}")
            st.markdown(f"**Your Answer:** {a}")
            if idx < len(st.session_state.question_scores):
                score = st.session_state.question_scores[idx]
                color = "#4CAF50" if score >= 7 else "#FF9800" if score >= 5 else "#F44336"
                st.markdown(f"**Score:** <span style='color:{color}; font-weight:bold;'>{score}/10</span>", unsafe_allow_html=True)
    
    # Download Report
    report = f"""
{st.session_state.current_role.upper()} INTERVIEW REPORT
{'='*50}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Overall Score: {st.session_state.overall_score}/10

METRICS:
{chr(10).join([f'- {k}: {v}/10' for k, v in st.session_state.metrics.items()])}

QUESTION SCORES:
{chr(10).join([f'Q{i+1}: {st.session_state.question_scores[i]}/10' for i in range(len(st.session_state.question_scores))])}

{'='*50}
FEEDBACK:
{st.session_state.final_feedback}

{'='*50}
TRANSCRIPT:
{chr(10).join([f'Q{i+1}: {q}\nA{i+1}: {a}\n' for i, (q, a) in enumerate(zip(st.session_state.questions, st.session_state.answers))])}
"""
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.download_button("📥 Download Report", report, 
                          f"{st.session_state.current_role.lower().replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                          use_container_width=True,
                          key="download_report_button")
        
        if st.button("🔄 Start New Interview", use_container_width=True, key="new_interview_button"):
            reset_interview()
            st.rerun()

# ----------------------------------
# FOOTER
# ----------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    <p>🚀 AI Job Interview Coach | Built with Streamlit & Gemini AI</p>
    <p>💡 Every interview is UNIQUE - Questions generated fresh each time for YOUR specific role!</p>
</div>
""", unsafe_allow_html=True)