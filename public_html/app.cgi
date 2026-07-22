#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
from wsgiref.handlers import CGIHandler

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем приложение из app.py
from app import app

# Запускаем через CGI
CGIHandler().run(app)