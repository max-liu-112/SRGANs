# SRGANs : Spectral Regularization for Combating Mode Collapse in GANs
Image generation on ImageNet. 
The latest version can be found here: https://arxiv.org/pdf/1908.10999.pdf where we introduce the dynamic compensation as a implementation of Spectral Regularization. Dynamic compensation works better on ImageNet.

Image generation on CIFAR-10 and STL-10 can be found: https://github.com/max-liu-112/SRGANs-Spectral-Regularization-GANs-
### References
-Kanglin Liu, Wenming Tang, Fei Zhou, Guoping Qiu. *Spectral Regularization for Combating Mode Collapse in GANs*. ICCV2019. [SRGANs]

* The implementation is Based on SNGANs https://github.com/pfnet-research/sngan_projection, 

* The setup and example code in this README are for training SRGANs on 4 GPUs.

### Experiment setup
please refer to SNGANs https://github.com/pfnet-research/sngan_projection

### SR method
Actually, SR method only adds few modification based on SN method. In this example, we do image generation on ImageNet. After the gradient update, we conduct dynamic compensation, which is implemented based on the 'SR' method in https://github.com/max-liu-112/SRGANs/blob/master/updater.py. In the next forward process, we use weight matrix w to do the convolutional operation, then the w has already been compensated. 

### Train the model

The defailt setting of Batch size is 2048. 

First, we train the model identical to SN-GANs. (No Spectral Regularization involved)

We strongly recommand you not to apply SR method in the beginning. Because SR need singulat value decompostion (SVD), which is rather computationally heavy. By the way, dynamic compensation guanrantee the spectral value not decrease. Actually, spectral values donnot drop in the begininig when using SN method. So we can apply SN method in the begining: 

`python train.py`

With such a setting, mode collapse begins at iteration=40k. 

<img src="https://github.com/max-liu-112/SRAGNs/blob/master/figures/fig1_is.jpg"  height="300" /><img src="https://github.com/max-liu-112/SRAGNs/blob/master/figures/fig2_fid.jpg" height="300"> 

Spectral Collapse is also observed and shown in the following figure.

<img src="https://github.com/max-liu-112/SRAGNs/blob/master/figures/fig3.jpg" height="300">


Then we resume the training with the snapshot at iterations=40k. Now we apply proposed SR to model.
(trun the updater args 'apply_SR' in confgis/config.yaml to 'True')
We can see in the following figure that applying SR avoid the mode collapse problem, and greatly improve the model performance.

<img src="https://github.com/max-liu-112/SRAGNs/blob/master/figures/fig4.jpg" height="300">

### Generated Images
SNGAN: iterations=40k

<img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SNGAN_40k_id204.png" height="270"/>      <img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SNGAN_40k_id323.png" height="270"/>      <img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SNGAN_40k_id946.png" height="270">

SNGAN: iterations=70k

<img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SNGAN_70k_id204.png" height="270"/>              <img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SNGAN_70k_id323.png" height="270"/>       <img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SNGAN_70k_id946.png" height="270">

SRGAN: iterations=70k

<img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SRGAN_70k_id204.png" height="270"/>       <img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SRGAN_70k_id323.png" height="270"/>       <img src="https://github.com/max-liu-112/SRGANs/blob/master/figures/SRGAN_70k_id946.png" height="270">


