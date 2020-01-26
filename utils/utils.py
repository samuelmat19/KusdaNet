import os
import glob
import re
import numpy as np
from common_definitions import tf, THRESHOLD_SIGMOID, IMAGE_INPUT_SIZE, K_SN
from sklearn.utils.class_weight import compute_class_weight
from tqdm import tqdm

def f1(y_true, y_pred): #taken from old keras source code
	# threshold y_pred
	y_pred = tf.cast(tf.math.greater_equal(y_pred, tf.cast(THRESHOLD_SIGMOID, tf.float32)), tf.float32)

	true_positives = tf.math.reduce_sum(tf.round(tf.clip_by_value(y_true * y_pred, 0, 1)), 0)
	possible_positives = tf.math.reduce_sum(tf.round(tf.clip_by_value(y_true, 0, 1)), 0)
	predicted_positives = tf.math.reduce_sum(tf.round(tf.clip_by_value(y_pred, 0, 1)), 0)
	precision = true_positives / (predicted_positives + tf.keras.backend.epsilon())
	recall = true_positives / (possible_positives + tf.keras.backend.epsilon())
	f1_val = 2*(precision*recall)/(precision+recall+tf.keras.backend.epsilon())
	return f1_val

def custom_sigmoid(x):
	"""
	This functions fit SVM case because it is close to max points on {-1,1}
	"""
	return 1 / (1 + tf.math.exp(-2*tf.math.exp(1.)*x))

def f1_svm(y_true, y_pred):
	y_pred = custom_sigmoid(y_pred)
	return f1(y_true, y_pred)

class AUC_SVM(tf.keras.metrics.AUC):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	def update_state(self, y_true, y_pred, sample_weight=None):
		y_pred = custom_sigmoid(y_pred)
		super().update_state(y_true, y_pred, sample_weight)

def get_and_mkdir(path):
	dir_modelckp = os.path.dirname(path)

	if not os.path.exists(dir_modelckp):
		os.makedirs(dir_modelckp)
	return dir_modelckp

def get_max_acc_weight(path):
	dir_modelckp = get_and_mkdir(path)

	model_weight_files = sorted(glob.glob(dir_modelckp + "/*.hdf5"), reverse=True)

	if len(model_weight_files) == 0:
		return False, 0

	max_epoch = None
	max_acc = None
	target_weight_file = None

	# look for target weight
	for mw_file in model_weight_files:
		basename = os.path.basename(mw_file)
		epoch_acc = re.search(r"[.](.*)[-](.*)[.]hdf5", basename)
		epoch = int(epoch_acc.group(1))
		acc = float(epoch_acc.group(2))

		if max_epoch is None:
			max_epoch = epoch
			max_acc = acc
			target_weight_file = mw_file
		else:
			if acc > max_acc:
				max_epoch = epoch
				max_acc = acc
				target_weight_file = mw_file

	return target_weight_file, max_epoch

def calculating_class_weights(y_true):
	number_dim = np.shape(y_true)[1]
	weights = np.empty([number_dim, 2])
	for i in tqdm(range(number_dim)):
		try:
			weights[i] = compute_class_weight('balanced', [0., 1.], y_true[:, i])
		except ValueError:
			weights[i] = np.ones(2)
	return weights

def get_weighted_loss(weights):
	def weighted_loss(y_true, y_pred):
		return tf.keras.backend.mean((weights[:,0]**(1-y_true))*(weights[:,1]**(y_true))*tf.keras.backend.binary_crossentropy(y_true, y_pred), axis=-1)
	return weighted_loss

from tensorflow.python.framework import ops
from tensorflow.python.ops import math_ops
from tensorflow.python.framework import smart_cond
def _maybe_convert_labels(y_true):
  """Converts binary labels into -1/1."""
  are_zeros = math_ops.equal(y_true, 0)
  are_ones = math_ops.equal(y_true, 1)
  is_binary = math_ops.reduce_all(math_ops.logical_or(are_zeros, are_ones))

  def _convert_binary_labels():
    # Convert the binary labels to -1 or 1.
    return 2. * y_true - 1.

  updated_y_true = smart_cond.smart_cond(is_binary,
                                         _convert_binary_labels, lambda: y_true)
  return updated_y_true

def squared_hinge(y_true, y_pred, reduction_bool=True):
	"""Computes the squared hinge loss between `y_true` and `y_pred`.
	Args:
	y_true: The ground truth values. `y_true` values are expected to be -1 or 1.
	  If binary (0 or 1) labels are provided we will convert them to -1 or 1.
	y_pred: The predicted values.
	Returns:
	Tensor with one scalar loss entry per sample.
	"""
	y_pred = ops.convert_to_tensor(y_pred)
	y_true = math_ops.cast(y_true, y_pred.dtype)
	y_true = _maybe_convert_labels(y_true)

	if reduction_bool:
		return tf.keras.backend.mean(
			math_ops.square(math_ops.maximum(1. - y_true * y_pred, 0.)), axis=-1)
	else:
		return math_ops.square(math_ops.maximum(1. - y_true * y_pred, 0.))

def get_square_hinge_weighted_loss(weights):
	# Different Error Costs
	def weighted_loss(y_true, y_pred):
		return tf.keras.backend.mean((weights[:,0]**(1-y_true))*(weights[:,1]**y_true)*squared_hinge(y_true, y_pred, reduction_bool=False), axis=-1)
	return weighted_loss


if __name__ == "__main__":
	# img = read_image_and_preprocess("../sample/00002032_012.png")
	a = np.random.randint(0, 2, size=10)