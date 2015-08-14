# --------------------------------------------------------
# Fast R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

"""Compute minibatch blobs for training a Fast R-CNN network."""

import numpy as np
import numpy.random as npr
import cv2
from fast_rcnn.config import cfg
from utils.blob import prep_im_for_blob, im_list_to_blob

def get_minibatch(roidb):
    """Given a roidb, construct a minibatch sampled from it."""
    num_images = len(roidb)
    assert(cfg.TRAIN.BATCH_SIZE % num_images == 0), \
        'num_images ({}) must divide BATCH_SIZE ({})'. \
        format(num_images, cfg.TRAIN.BATCH_SIZE)

    # Get the input image blob, formatted for caffe
    im_blob, im_scales, im_indexes = _get_image_blob(roidb)

    # Now, build the region of interest and label blobs
    rois_blob = np.zeros((0, 6), dtype=np.float32)
    labels_blob = np.zeros((0), dtype=np.float32)
    sublabels_blob = np.zeros((0), dtype=np.float32)

    for i in xrange(len(im_indexes)):

        im_i = im_indexes[i]
        im_rois = roidb[im_i]['boxes']
        labels = roidb[im_i]['gt_classes']
        sublabels = roidb[im_i]['gt_subclasses']

        # Add to RoIs blob
        rois = _project_im_rois(im_rois, im_scales[i])
        batch_ind = i * np.ones((rois.shape[0], 1))
        image_ind = im_i * np.ones((rois.shape[0], 1))
        rois_blob_this_image = np.hstack((batch_ind, image_ind, rois))
        rois_blob = np.vstack((rois_blob, rois_blob_this_image))

        # Add to labels, bbox targets, and bbox loss blobs
        labels_blob = np.hstack((labels_blob, labels))
        sublabels_blob = np.hstack((sublabels_blob, sublabels))

    # For debug visualizations
    # _vis_minibatch(im_blob, rois_blob, labels_blob, sublabels_blob)

    blobs = {'data': im_blob,
             'gt_rois': rois_blob,
             'gt_labels': labels_blob}

    if cfg.TRAIN.SUBCLS:
        blobs['gt_sublabels'] = sublabels_blob

    return blobs

def _get_image_blob(roidb):
    """Builds an input blob from the images in the roidb at the different scales.
    """
    num_images = len(roidb)
    processed_ims = []
    im_scales = []
    im_indexes = []

    for i in xrange(num_images):
        # read image
        im = cv2.imread(roidb[i]['image'])
        if roidb[i]['flipped']:
            im = im[:, ::-1, :]

        im_orig = im.astype(np.float32, copy=True)
        im_orig -= cfg.PIXEL_MEANS

        # build image pyramid
        im_shape = im_orig.shape
        im_size_min = np.min(im_shape[0:2])
        im_size_max = np.max(im_shape[0:2])

        for target_size in cfg.TRAIN.SCALES:
            im_scale = float(target_size) / float(im_size_min)

            # Prevent the biggest axis from being more than MAX_SIZE
            if np.round(im_scale * im_size_max) > cfg.TRAIN.MAX_SIZE:
                im_scale = float(cfg.TRAIN.MAX_SIZE) / float(im_size_max)

            im = cv2.resize(im_orig, None, None, fx=im_scale, fy=im_scale,
                        interpolation=cv2.INTER_LINEAR)

            processed_ims.append(im)
            im_scales.append(im_scale)
            im_indexes.append(i)

    # Create a blob to hold the input images
    blob = im_list_to_blob(processed_ims)

    return blob, im_scales, im_indexes

def _project_im_rois(im_rois, im_scale_factor):
    """Project image RoIs into the rescaled training image."""
    rois = im_rois * im_scale_factor
    return rois

def _vis_minibatch(im_blob, rois_blob, labels_blob, sublabels_blob):
    """Visualize a mini-batch for debugging."""
    import matplotlib.pyplot as plt
    for i in xrange(rois_blob.shape[0]):
        rois = rois_blob[i, :]
        im_ind = rois[0]
        roi = rois[2:]
        im = im_blob[im_ind, :, :, :].transpose((1, 2, 0)).copy()
        im += cfg.PIXEL_MEANS
        im = im[:, :, (2, 1, 0)]
        im = im.astype(np.uint8)
        cls = labels_blob[i]
        subcls = sublabels_blob[i]
        plt.imshow(im)
        print 'class: ', cls, ' subclass: ', subcls
        plt.gca().add_patch(
            plt.Rectangle((roi[0], roi[1]), roi[2] - roi[0],
                          roi[3] - roi[1], fill=False,
                          edgecolor='r', linewidth=3)
            )
        plt.show()
