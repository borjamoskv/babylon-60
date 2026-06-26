import sys
from cortex.engine import CortexEngine
import cortex.database.core

print(dir(cortex.database.core))
print("CortexConnection" in dir(cortex.database.core))
