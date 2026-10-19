#!/bin/bash
# Seed-repeat runs (seed 7) of the two 320 px models, same settings as the originals, own checkpoints/logs.
cd /c/Users/sndps/Downloads/ChestXray-NIHCC/pipeline
PY=/c/Users/sndps/AppData/Local/Programs/Python/Python311/python.exe
export CXR_IMG=320 CXR_EMA=0.999 CXR_PIN=0 CXR_SEED=7
run() {  # $1=arch $2=epochs $3=log
  for i in 1 2 3 4 5 6; do
    CXR_ARCH=$1 CXR_EPOCHS=$2 CXR_BATCH=16 CXR_ACCUM=2 $PY -u train.py >> $3 2>&1
    grep -q "mean test AUROC" $3 && break
    echo "RESTART $i" >> $3; sleep 10
  done
}
run convnext_tiny.fb_in22k_ft_in1k 4 outputs/train_stdout_convnext_320_seed7.log
run densenet121 5 outputs/train_stdout_densenet_320_seed7.log
