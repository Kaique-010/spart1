from pathlib import Path
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-r7t_y++!$nk1k5)cj-&qta&=dri+13+!@t0x9xfnelnd76^6xv'
DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'agent_ai',
    'rest_framework',
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'spart.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spart.wsgi.application'


# Databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },

    'postgresql': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'spart',
        'USER': 'postgres',
        'PASSWORD': '@spartacus201@',
        'HOST': 'db', 
        'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-BR'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Para API pública
    ],
}

# drf-spectacular Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Spartacus AI Agent API',
    'DESCRIPTION': '''
    API do Agente AI Spartacus - Sistema de assistente virtual inteligente
    
    ## Funcionalidades Principais
    
    ### 🤖 Agente AI Inteligente
    - Processamento de linguagem natural com GPT-3.5-turbo
    - Busca vetorial usando embeddings OpenAI
    - Respostas contextualizadas baseadas em manuais
    - Geração automática de áudio das respostas
    
    ### 📚 Gestão de Conhecimento
    - Processamento automático de manuais web
    - Extração e indexação de conteúdo
    - Busca por similaridade semântica
    - Armazenamento otimizado de embeddings
    
    ### 🚀 Recursos Avançados
    - Streaming de respostas em tempo real (SSE)
    - Geração assíncrona de áudio
    - API RESTful completa
    - Documentação interativa
    
    ## Modelos de IA Utilizados
    - **Embeddings**: text-embedding-ada-002 (OpenAI)
    - **Chat**: gpt-3.5-turbo (OpenAI)
    - **Áudio**: gTTS (Google Text-to-Speech)
    
    ## Autenticação
    Esta API é pública e não requer autenticação para uso básico.
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Servidor de Desenvolvimento'
        },
        {
            'url': 'https://api.spartacus.com',
            'description': 'Servidor de Produção'
        }
    ],
    'TAGS': [
        {
            'name': 'Agente AI',
            'description': 'Endpoints principais para interação com o agente'
        },
        {
            'name': 'Manuais',
            'description': 'Gestão e processamento de manuais'
        },
        {
            'name': 'Respostas',
            'description': 'Visualização de respostas armazenadas'
        }
    ],
    'EXTERNAL_DOCS': {
        'description': 'Central de Ajuda Spartacus',
        'url': 'https://spartacus.movidesk.com/kb/'
    },
    'CONTACT': {
        'name': 'Equipe Spartacus',
        'email': 'suporte@spartacus.com.br'
    },
    'LICENSE': {
        'name': 'Proprietary License',
        'url': 'https://spartacus.com.br/license'
    }
}

# Configuração da OpenAI API
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

