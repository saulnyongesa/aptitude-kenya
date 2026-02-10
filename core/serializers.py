from rest_framework import serializers
from .models import User, Classroom, Exam, Question, Choice, Submission, ProctorLog

# --- 1. User Serializer ---
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'fullname', 'email', 'is_tutor', 'is_student', 'school_name', 'registration_id']
        read_only_fields = ['is_tutor', 'is_student']

# --- 2. Exam & Question Serializers ---
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'label', 'text']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'choices', 'order']
        # Note: We EXCLUDE 'correct_labels' here so students can't inspect 
        # the JSON in the browser to find the answer!

class ExamSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'start_time', 'end_time', 'attempts_allowed', 
            'back_btn_enabled', 'show_results_immediately', 'question_count'
        ]

# --- 3. Classroom Serializer ---
class ClassroomSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source='tutor.fullname', read_only=True)
    student_count = serializers.IntegerField(source='students.count', read_only=True)
    
    class Meta:
        model = Classroom
        fields = ['id', 'name', 'room_id', 'tutor_name', 'student_count', 'created_at']

# --- 4. Performance & Security Serializers ---
class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.fullname', read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'student_name', 'exam_title', 'score', 'completed', 'attempt_number', 'submitted_at']

class ProctorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProctorLog
        fields = ['id', 'violation_type', 'timestamp']