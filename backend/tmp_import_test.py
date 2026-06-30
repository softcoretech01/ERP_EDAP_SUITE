import sys
sys.path.append('d:/ERP Assitant/backend')
from app.services import qdrant_service
from app.api import debug
print('qdrant_service imported:', hasattr(qdrant_service, 'qdrant_service'))
print('debug module imported:', hasattr(debug, 'router'))
