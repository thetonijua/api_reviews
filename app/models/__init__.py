# Importar ambos modelos juntos para que SQLAlchemy pueda resolver la relación
# Empresa <-> Resena aunque un script importe solo uno de ellos.
from app.models.empresa import Empresa  # noqa: F401
from app.models.resena import Resena  # noqa: F401
