import os
import sys
import math

import numpy as np
from PIL import Image
import scipy.linalg

import chainer
import chainer.cuda
from chainer import Variable
from chainer import serializers
from chainer import cuda
import chainer.functions as F

sys.path.append(os.path.dirname(__file__))
sys.path.append('../')
from source.inception.inception_score import inception_score, Inception
from source.links.sn_convolution_2d import SNConvolution2D
from source.functions.max_sv import max_singular_value
from numpy.linalg import svd


def gen_images(gen, n=50000, batchsize=100):
    ims = []
    xp = gen.xp
    for i in range(0, n, batchsize):
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            x   = gen(batchsize)
        x= chainer.cuda.to_cpu(x.data)
        x = np.asarray(np.clip(x * 127.5 + 127.5, 0.0, 255.0), dtype=np.uint8)
        ims.append(x)
    ims = np.asarray(ims)
    _, _, _, h, w = ims.shape
    ims = ims.reshape((n, 3, h, w))
    return ims


def gen_images_with_condition(gen, c=0, n=500, batchsize=100):
    ims = []
    xp = gen.xp
    for i in range(0, n, batchsize):
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            y = xp.asarray([c] * batchsize, dtype=xp.int32)
            x = gen(batchsize, y=y)
        x = chainer.cuda.to_cpu(x.data)
        x = np.asarray(np.clip(x * 127.5 + 127.5, 0.0, 255.0), dtype=np.uint8)
        ims.append(x)
    ims = np.asarray(ims)
    _, _, _, h, w = ims.shape
    ims = ims.reshape((n, 3, h, w))
    return ims


def sample_generate_light(gen, dst, rows=5, cols=5, seed=0):
    @chainer.training.make_extension()
    def make_image(trainer):
        np.random.seed(seed)
        n_images = rows * cols
        x = gen_images(gen, n_images, batchsize=n_images)
        _, _, H, W = x.shape
        x = x.reshape((rows, cols, 3, H, W))
        x = x.transpose(0, 3, 1, 4, 2)
        x = x.reshape((rows * H, cols * W, 3))
        preview_dir = '{}/preview'.format(dst)
        preview_path = preview_dir + '/image_latest.png'
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)
        Image.fromarray(x).save(preview_path)

    return make_image


def sample_generate(gen, dst, rows=10, cols=10, seed=0):
    """Visualization of rows*cols images randomly generated by the generator."""
    @chainer.training.make_extension()
    def make_image(trainer):
        np.random.seed(seed)
        n_images = rows * cols
        x = gen_images(gen, n_images, batchsize=n_images)
        _, _, h, w = x.shape
        x = x.reshape((rows, cols, 3, h, w))
        x = x.transpose(0, 3, 1, 4, 2)
        x = x.reshape((rows * h, cols * w, 3))
        preview_dir = '{}/preview'.format(dst)
        preview_path = preview_dir + '/image{:0>8}.png'.format(trainer.updater.iteration)
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)
        Image.fromarray(x).save(preview_path)

    return make_image


def sample_generate_conditional(gen, dst, rows=10, cols=10, n_classes=1000, seed=0):
    """Visualization of rows*cols images randomly generated by the generator."""
    classes = np.asarray(np.arange(cols) * (n_classes / cols), dtype=np.int32)

    @chainer.training.make_extension()
    def make_image(trainer=None):
        np.random.seed(seed)
        xp = gen.xp
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            x = []
            for c in classes:
                x.append(gen_images_with_condition(gen, c=c, n=rows, batchsize=rows))
            x = np.concatenate(x, 0)
        _, _, h, w = x.shape
        x = x.reshape((rows, len(classes), 3, h, w))
        x = x.transpose(0, 3, 1, 4, 2)
        x = x.reshape((rows * h, len(classes) * w, 3))

        preview_dir = '{}/preview'.format(dst)
        preview_path = preview_dir + '/image{:0>8}.png'.format(
            trainer.updater.iteration if trainer is not None else None)
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)
        Image.fromarray(x).save(preview_path)

    return make_image


def load_inception_model(path=None):
    path = path if path is not None else "%s/inception/inception_score.model" % os.path.dirname(__file__)
    model = Inception()
    serializers.load_hdf5(path, model)
    model.to_gpu()
    return model


def calc_inception(gen, batchsize=100, dst=None, path=None, n_ims=50000, splits=10):
    @chainer.training.make_extension()
    def evaluation(trainer=None):
        model = load_inception_model(path)
        ims = gen_images(gen, n_ims, batchsize=batchsize).astype("f")
        mean, std = inception_score(model, ims, splits=splits)
        chainer.reporter.report({
            'inception_mean': mean,
            'inception_std': std
        })
        if dst is not None:
            preview_dir = '{}/IS.txt'.format(dst)
            with open(preview_dir, 'a', encoding='ascii') as f:
                f.write(str(trainer.updater.iteration))
                f.write(':')
                f.write(str(mean))
                f.write(',  ')
                f.write(str(std))
                f.write('\n')

    return evaluation


def get_mean_cov(model, ims, batch_size=100):
    n, c, w, h = ims.shape
    n_batches = int(math.ceil(float(n) / float(batch_size)))
    xp = model.xp
    #print('Batch size:', batch_size)
    #print('Total number of images:', n)
    #print('Total number of batches:', n_batches)
    ys = xp.empty((n, 2048), dtype=xp.float32)
    for i in range(n_batches):
        #print('Running batch', i + 1, '/', n_batches, '...')
        batch_start = (i * batch_size)
        batch_end = min((i + 1) * batch_size, n)

        ims_batch = ims[batch_start:batch_end]
        ims_batch = xp.asarray(ims_batch)  # To GPU if using CuPy
        ims_batch = Variable(ims_batch)

        # Resize image to the shape expected by the inception module
        if (w, h) != (299, 299):
            ims_batch = F.resize_images(ims_batch, (299, 299))  # bilinear

        # Feed images to the inception module to get the features
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            y = model(ims_batch, get_feature=True)
        ys[batch_start:batch_end] = y.data

    mean = xp.mean(ys, axis=0).get()
    # cov = F.cross_covariance(ys, ys, reduce="no").datasets.get()
    cov = np.cov(ys.get().T)
    return mean, cov


def monitor_largest_singular_values(dis, dst):
    @chainer.training.make_extension()
    def evaluation(trainer=None):
        def _l2normalize(v, eps=1e-12):
            return v / (((v ** 2).sum()) ** 0.5 + eps)

        xp = dis.xp
        links = [[name, link] for name, link in sorted(dis.namedlinks())]
        sigmas = []

        for name, link in links:
            if isinstance(link, SNConvolution2D):
                W, u = link.W, link.u
                W_mat = W.reshape(W.shape[0], -1)
                sigma, _, _ = max_singular_value(W_mat, u)
                W_bar = cuda.to_cpu((W_mat.data / xp.squeeze(sigma.data)))
                _, s, _ = svd(W_bar)
                _sigma = s[0]
                print(name.strip('/'), _sigma)
                sigmas.append(s)

        sigmas = np.asarray(sigmas)
        print(sigmas.shape)
        if dst is not None:
            preview_dir = '{}/dis_sigmas'.format(dst)
            if not os.path.exists(preview_dir):
                os.makedirs(preview_dir)
            i = 0
            for s in sigmas:
                preview_path = preview_dir + '/sigmas_{:0>8}_{}.txt'.format(
                    trainer.updater.iteration if trainer is not None else None, i)
                np.savetxt(preview_path, s, delimiter='\n')
                i = i + 1
    return evaluation


def FID(m0, c0, m1, c1):
    ret = 0
    ret += np.sum((m0 - m1) ** 2)
    ret += np.trace(c0 + c1 - 2.0 * scipy.linalg.sqrtm(np.dot(c0, c1)))
    return np.real(ret)


def calc_FID(gen, batchsize=100, stat_file="%s/cifar-10-fid.npz" % os.path.dirname(__file__), dst=None, path=None,
             n_ims=5000):
    """Frechet Inception Distance proposed by https://arxiv.org/abs/1706.08500"""

    @chainer.training.make_extension()
    def evaluation(trainer=None):
        model = load_inception_model(path)
        stat = np.load(stat_file)
        ims = gen_images(gen, n_ims, batchsize=batchsize).astype("f")
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            mean, cov = get_mean_cov(model, ims)
        fid = FID(stat["mu"][:], stat["sigma"][:], mean, cov)
        chainer.reporter.report({
            'FID': fid,
        })
        if dst is not None:
            preview_dir = '{}/FID.txt'.format(dst)
            with open(preview_dir, 'a', encoding='ascii') as f:
                f.write(str(trainer.updater.iteration))
                f.write(':')
                f.write(str(fid))
                f.write('\n')
    return evaluation
