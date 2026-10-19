#!/bin/bash
# Launch ConvNeXt-Tiny @320; auto-restart (resumes from last.pt) if the process dies without finishing.
cd /c/Users/sndps/Downloads/ChestXray-NIHCC/pipeline
PY=/c/Users/sndps/AppData/Local/Programs/Python/Python311/python.exe
export CXR_IMG=320 CXR_ARCH=convnext_tiny.fb_in22k_ft_in1k CXR_EPOCHS=4 CXR_EMA=0.999 CXR_PIN=0
L=outputs/train_stdout_convnext_320.log
for i in 1 2 3 4 5 6; do
  CXR_BATCH=16 CXR_ACCUM=2 $PY -u train.py >> $L 2>&1
  grep -q "mean test AUROC" $L && break
  echo "RESTART $i" >> $L
  sleep 10
done
