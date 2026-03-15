#!/bin/bash
# Downgrade Numpy to 1.26.4 to fix binary incompatibility with system Picamera2
echo "📉 Downgrading Numpy to 1.26.4..."
pip install "numpy<2.0.0" 

# Verify
echo "✅ Verification:"
python -c "import numpy; print(f'Numpy Version: {numpy.__version__}')"
