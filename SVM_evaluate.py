"""
Train normal model with binary XE as loss function
"""
from common_definitions import *
from datasets.cheXpert_dataset import read_dataset
from utils.utils import *
from utils.visualization import *
from models.multi_class import *

if __name__ == "__main__":
	model = model_MC_SVM()
	if LOAD_WEIGHT_BOOL:
		target_model_weight, _ = get_max_acc_weight(MODELCKP_PATH)
		if target_model_weight:  # if weight is Found
			model.load_weights(target_model_weight)
		else:
			print("[Load weight] No weight is found")

	# get the dataset
	test_dataset = read_dataset(CHEXPERT_TEST_TARGET_TFRECORD_PATH if EVAL_CHEXPERT else CHESTXRAY_TEST_TARGET_TFRECORD_PATH, CHEXPERT_DATASET_PATH if EVAL_CHEXPERT else CHESTXRAY_DATASET_PATH, evaluation_mode=True)

	test_label_nps = np.empty((CHEXPERT_TEST_N if EVAL_CHEXPERT else CHESTXRAY_TEST_N, 5), dtype=np.float32)
	test_img_nps = np.empty((CHEXPERT_TEST_N if EVAL_CHEXPERT else CHESTXRAY_TEST_N, IMAGE_INPUT_SIZE, IMAGE_INPUT_SIZE, 1), dtype=np.float32)
	# get the ground truth labels
	for i_d, (test_img, test_label) in enumerate(test_dataset):
		test_label_nps[i_d*BATCH_SIZE:i_d*BATCH_SIZE + BATCH_SIZE] = test_label
		test_img_nps[i_d*BATCH_SIZE:i_d*BATCH_SIZE + BATCH_SIZE] = test_img


	# Evaluate the model on the test data using `evaluate`
	results = custom_sigmoid(model.predict(test_img_nps, batch_size=BATCH_SIZE*2, verbose=1)).numpy()
	results = results[:, TRAIN_FIVE_CATS_INDEX]

	print("F1: ", np.mean(f1(test_label_nps, results).numpy()))

	plot_roc(test_label_nps, results)