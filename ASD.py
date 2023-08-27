import warnings

import numpy as np
warnings.filterwarnings("ignore", message="Creating an ndarray from ragged nested sequences")
warnings.filterwarnings("ignore", category = FutureWarning)

import pandas as pd

import importlib as il

from problem import get_cv

from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_validate
from sklearn.model_selection import cross_val_predict
from sklearn import metrics
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.model_selection import StratifiedKFold

import seaborn as sns

import matplotlib.pyplot as plt

from os.path import exists

import csv as cs


def load_data():
  #Load the data
  from problem import get_train_data
  from problem import get_test_data

  data_train, labels_train = get_train_data()
  data_test, labels_test = get_test_data()
  return data_train, labels_train, data_test, labels_test

def print_gender_info(data_train, data_test):
  #print gender data
  print("Training Data Gender Data")
  print(data_train["participants_sex"].value_counts())

  print("Test Data Gender Data")
  print(data_test["participants_sex"].value_counts())

def evaluation_predict(X,y, Classifier, FeatureExtractor):
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  # Note: in the cross_validate function, they use StratifiedShuffleSplit which allows for resampling
  pipe = make_pipeline(FeatureExtractor(), Classifier())
  cv_custom = StratifiedKFold(n_splits=5, shuffle = True, random_state=42) 

  return cross_val_predict(pipe, X, y, cv=cv_custom, verbose=1, n_jobs=2, method='predict')

def gender_ratio_per_fold(data_train, labels_train):
  #gender ratio per cross-validation fold
  cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42) 
  data_train_sex = np.array(data_train['participants_sex'])
  fold_number = 1
  for train_index, test_index in cv.split(data_train, labels_train):
      train = data_train_sex[train_index]
      test = data_train_sex[test_index]

      train_male_count = np.count_nonzero(train == 'M')
      train_female_count = np.count_nonzero(train == 'F')

      test_male_count = np.count_nonzero(test == 'M')
      test_female_count = np.count_nonzero(test == 'F')

      print("Fold ", fold_number, ": Training Gender Proportion ", "Female 1 : Male ", round(train_male_count/train_female_count, 2), sep = "")
      print("Fold ", fold_number, ": Test Gender Proportion ", "Female 1 : Male ", round(test_male_count/test_female_count, 2), sep = "")
      fold_number += 1

def load_submission(name):
  classifier_module = il.import_module("submissions."+name+".classifier")
  FeatureExtractor_module = il.import_module("submissions."+name+".feature_extractor")
  return classifier_module.Classifier(), FeatureExtractor_module.FeatureExtractor()

def download_data():
  # Make sure you download the functional data, if it is not already stored on your drive
  from download_data import fetch_fmri_time_series
  fetch_fmri_time_series(atlas='all')

def initialise_predictions(data_train, labels_train, Classifier, FeatureExtractor):
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  return evaluation_predict(data_train, labels_train, Classifier, FeatureExtractor)

def check_for_saved_file(seed):
  return exists("saved_outcomes/"+str(seed)+".txt")

def save_predictions(seed, predictions):
  warnings.filterwarnings("ignore", message=".*`np.*` is a deprecated alias.*")

  predictions.to_csv("saved_outcomes/"+str(seed)+".txt", index = True)

def load_predictions(seed):

  return pd.read_csv("saved_outcomes/"+str(seed)+".txt")

def plot_auc(labels_train, predictions, name):
  #define auc-roc score
  auc_roc_score = roc_auc_score(labels_train, predictions)

  #print decimal value
  print("AUC-ROC Score:", auc_roc_score)

  #determine false positive rate and true positive rate
  fpr, tpr, thresholds = roc_curve(labels_train, predictions)

  # Plotting the AUC-ROC curve
  plt.plot(fpr, tpr, label='AUC = %0.3f' % auc_roc_score)
  plt.plot([0, 1], [0, 1], 'k--')  # Diagonal line representing random guessing
  plt.xlabel('False Positive Rate')
  plt.ylabel('True Positive Rate')
  plt.title('AUC-ROC Curve for ' + name)
  plt.legend(loc='lower right')
  plt.show()
  return auc_roc_score

def general_accuracy_old(predictions, data_train, labels_train, seed):
  
  # print("General Accurracy: True Positive and True Negative Accuracy")
  # print(predictions)
  # print(cv_split)
  # print(data_train)
  # print(labels_train)

  warnings.filterwarnings("ignore", message=".*`np.*` is a deprecated alias.*")
  cv_ga = StratifiedKFold(n_splits=5, shuffle = True, random_state = seed) 
  cv_ga_split = cv_ga.split(data_train, labels_train)

  fold_pred = [predictions[test] for train, test in cv_ga.split(data_train, labels_train)]
  fold_labels = [np.array(labels_train)[test] for train, test in cv_ga.split(data_train, labels_train)]
  data_train_sex = np.array(data_train['participants_sex'])
  i = 0
  fold_results = []
  for train_index, test_index in cv_ga_split:

    male_accuracy = 0
    male_total = 0
    female_accuracy = 0
    female_total = 0

    train = data_train_sex[train_index]
    test = data_train_sex[test_index]

    for index in range(len(fold_pred[i])): 
      if test[index] == 'M':
        male_total += 1
        if round(fold_pred[i][index]) == fold_labels[i][index]:
          male_accuracy += 1
      else:
        female_total += 1
        if round(fold_pred[i][index]) == fold_labels[i][index]:
          female_accuracy += 1
    i += 1
    male_ga = round(male_accuracy/male_total*100, 2)
    female_ga = round(female_accuracy/female_total*100, 2)
    ga_score = male_ga-female_ga
    print("Male: ", male_accuracy, " out of ", male_total,", ", male_ga, "%. Female: ", female_accuracy, " out of ", female_total, ", ", female_ga, "%. Total participants: ", female_total + male_total, sep="")
    if ga_score != 0:
      fold_results.append((np.abs(round(ga_score, 2)), round(abs(ga_score)/-ga_score))) #1 = F, -1 = M
    else:
      fold_results.append((np.abs(round(ga_score, 2)), 0)) #1 = F, -1 = M
  # print("Fold Results: ", fold_results)
  return fold_results

def train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor):
  #Create crossvalidation code
  # folds = 1
  fold_results = []
  cv_custom = StratifiedKFold(n_splits=5, shuffle = True, random_state=42) 

  for train, test in cv_custom.split(data_train, labels_train):


    dataframe_indices = data_train.index.values.copy()
    train_dataset = pd.DataFrame(index = dataframe_indices[train]) #initialise dataframe with key values with unique acquisition

    train_dataset.loc[:, data_train.columns] = data_train.loc[dataframe_indices[train]] #Copy all dataframe information w.r.t key values
    train_dataset.index.name = "subject_id"

    train_labels = labels_train[train]
    
    #Train the model on the full training dataset
    pipe = make_pipeline(FeatureExtractor(), Classifier())

    pipe.fit(train_dataset, train_labels)

    #Test the model on the external dataset (data_test)
    predictions_external = np.round(pipe.predict(data_test))

    fold_results.append(predictions_external)

    # Evaluate the model's performance on the external dataset
    # accuracy_external = accuracy_score(labels_test, predictions_external)
    # print("External Dataset Accuracy of Fold:", folds, "at", round(accuracy_external*100, 2), "%.")
    # folds += 1
  return fold_results

def create_dataframe(name, fold_stat_results):

  dataframe_names = [name + "-overall", name + "-male", name + "-female"]
  dataframe_contents = {"submission": dataframe_names}

  fold_number = 1
  for fold in fold_stat_results:
    TP = []
    FP = []
    FN = []
    TN = []
    AUC = []
    for results in fold:
      print("Fold results", results)
      TP.append(results[0])
      FP.append(results[1])
      FN.append(results[2])
      TN.append(results[3])
      AUC.append(results[4])
    dataframe_contents["TP"+"_"+str(fold_number)] = TP.copy()
    dataframe_contents["FP"+"_"+str(fold_number)] = FP.copy()
    dataframe_contents["FN"+"_"+str(fold_number)] = FN.copy()
    dataframe_contents["TN"+"_"+str(fold_number)] = TN.copy()
    dataframe_contents["AUC"+"_"+str(fold_number)] = AUC.copy()
    fold_number += 1
  # print(dataframe_contents)
  dataframed_results = pd.DataFrame(dataframe_contents)
  dataframed_results.set_index("submission", inplace=True)
  return dataframed_results

def process_results(raw_results, labels, sex):
  result = []
  for predicted_results in raw_results:
    result.append(determine_statistics(labels, predicted_results, sex))
  return result
      
def determine_statistics(labels, results, sex):     
  male_results = results[sex[0]]
  male_labels = labels[sex[0]]
  female_results = results[sex[1]]
  female_labels = labels[sex[1]]

  overall_true_positive = 0
  overall_false_positive = 0
  overall_true_negative = 0
  overall_false_negative = 0

  male_true_positive = 0
  male_false_positive = 0
  male_true_negative = 0
  male_false_negative = 0

  female_true_positive = 0
  female_false_positive = 0
  female_true_negative = 0
  female_false_negative = 0

  i = 0
  while i < len(labels):
    if labels[i] == 1 and results[i] == 1:
      overall_true_positive += 1
    elif results[i] == 0 and labels[i] == 1:
      overall_false_negative += 1
    elif results[i] == 1 and labels[i] == 0:
      overall_false_positive += 1
    elif labels[i] == 0 and results[i] == 0:
      overall_true_negative += 1
    i += 1
  i = 0
  while i < len(male_labels):
    if male_labels[i] == 1 and male_results[i] == 1:
      male_true_positive += 1
    elif male_results[i] == 0 and male_labels[i] == 1:
      male_false_negative += 1
    elif male_results[i] == 1 and male_labels[i] == 0:
      male_false_positive += 1
    elif male_labels[i] == 0 and male_results[i] == 0:
      male_true_negative += 1
    i += 1
  i = 0
  while i < len(female_labels):
    if female_labels[i] == 1 and female_results[i] == 1:
      female_true_positive += 1
    elif female_results[i] == 0 and female_labels[i] == 1:
      female_false_negative += 1
    elif female_results[i] == 1 and female_labels[i] == 0:
      female_false_positive += 1
    elif female_labels[i] == 0 and female_results[i] == 0:
      female_true_negative += 1
    i += 1

  overall_fpr, overall_tpr, overall_thresholds = metrics.roc_curve(labels, results)
  male_fpr, male_tpr, male_thresholds = metrics.roc_curve(male_labels, male_results)
  female__fpr, female__tpr, female_thresholds = metrics.roc_curve(female_labels, female_results)

  overall_auc = metrics.auc(overall_fpr, overall_tpr)
  male_auc = metrics.auc(male_fpr, male_tpr)
  female_auc = metrics.auc(female__fpr, female__tpr)

  return [(overall_true_positive, overall_false_positive, overall_false_negative, overall_true_negative, overall_auc), 
          (male_true_positive, male_false_positive, male_false_negative, male_true_negative, male_auc), 
          (female_true_positive, female_false_positive, female_false_negative, female_true_negative, female_auc)]

def auc_roc(results, seed):
  
  test_names = results.index.values.tolist()
  headings = results.columns.values.tolist()

  auc = []
  names = []

  i = 1
  while ("AUC"+"_"+str(i)) in headings:
    AUC_fold = results["AUC"+"_"+str(i)].values.tolist()

    j = 0
    while j < len(AUC_fold):
      auc.append(AUC_fold[j])
      j += 1

    k = 0
    while k < len(test_names):
      names.append(test_names[k]+"-"+str(i))
      k += 1
    i += 1
  consolidated_test_names = []
  auc_sex = []
  sex = []

  l = 0
  while l < len(names):
    split_names = str.split(names[l], "-")
    test_name = split_names[0]
    if split_names[1] != "overall":
      sex.append(split_names[1])
      consolidated_test_names.append(test_name)
      auc_sex.append(auc[l])

    l += 1
  
  generalised_submission_names = []
  m = 0
  while m < len(auc):
    auc[m] *= 100
    m += 1
  
  eo_df = pd.DataFrame({"Submissions": consolidated_test_names,
                        "Results": auc_sex,
                        "Sex": sex})

  sns.set_theme(style="whitegrid")
  plot = sns.violinplot(data=eo_df, x="Submissions", y="Results", split=True, hue="Sex", inner="stick")
  plot.set_title('AUC-ROC Performance of 10 Best Submissions: Seed '+str(seed))
  plot.set_xticklabels(plot.get_xticklabels(), rotation = 90)  
  plot.set_xlabel('Submissions')
  plot.set_ylabel('AUC (%)')
  plt.show()

def general_accuracy(results, seed):

  test_names = results.index.values.tolist()
  headings = results.columns.values.tolist()

  ga = []
  names = []

  i = 1
  while ("TP"+"_"+str(i)) in headings:
    TP_fold = results["TP"+"_"+str(i)].values.tolist()
    FP_fold = results["FP"+"_"+str(i)].values.tolist()
    FN_fold = results["FN"+"_"+str(i)].values.tolist()
    TN_fold = results["TN"+"_"+str(i)].values.tolist()

    j = 0
    while j < len(TP_fold):
      ga.append((TP_fold[j] + TN_fold[j]) / (TP_fold[j] + FP_fold[j] + FN_fold[j] + TN_fold[j]))
      j += 1

    k = 0
    while k < len(test_names):
      names.append(test_names[k]+"-"+str(i))
      k += 1
    i += 1

  consolidated_test_names = []
  ga_sex = []
  sex = []

  l = 0
  while l <len(names):
    split_names = str.split(names[l], "-")
    test_name = split_names[0]
    if split_names[1] != "overall":
      sex.append(split_names[1])
      consolidated_test_names.append(test_name)
      ga_sex.append(ga[l])
    l += 1

  eo_df = pd.DataFrame({"Submissions": consolidated_test_names,
                        "Sex": sex,
                        "Results": ga_sex})


  sns.set_theme(style="whitegrid")
  plot = sns.violinplot(data=eo_df, x="Submissions", y="Results",  split = True, hue="Sex", inner="stick")
  plot.set_title('General Accuracy  Performance of 10 Best Submissions: Seed '+str(seed))
  plot.set_xticklabels(plot.get_xticklabels(), rotation = 90)
  plot.set_xlabel('Submissions')
  plot.set_ylabel('Accuracy (%)')
  plot.legend(loc=(0, 0))
  plt.show()

def equal_opportunity(results, seed):

  test_names = results.index.values.tolist()
  headings = results.columns.values.tolist()

  tpr = []
  names = []  
  
  i = 1
  while ("TP"+"_"+str(i)) in headings:
    TP_fold = results["TP"+"_"+str(i)].values.tolist()
    # FP_fold = results["FP"+"_"+str(i)].values.tolist()
    FN_fold = results["FN"+"_"+str(i)].values.tolist()
    # TN_fold = results["TN"+"_"+str(i)].values.tolist()

    j = 0
    while j < len(TP_fold):
      tpr.append(TP_fold[j]/(TP_fold[j] + FN_fold[j]))
      j += 1

    k = 0
    while k < len(test_names):
      names.append(test_names[k]+"-"+str(i))
      k += 1
    i += 1

  consolidated_test_names = []
  eo = []

  l = 0
  while l <len(names):
    split_names = str.split(names[l], "-")
    test_name = split_names[0]+"-"+split_names[2]
    if split_names[1] != "overall":
      if test_name not in consolidated_test_names:
        consolidated_test_names.append(test_name)
        eo.append(tpr[l])
      else:
        eo[consolidated_test_names.index(test_name)] -= tpr[l]
    l += 1
  
  generalised_submission_names = []
  m = 0
  while m < len(eo):
    eo[m] *= 100
    consolidated_test_names_split = str.split(consolidated_test_names[m], "-")
    generalised_submission_names.append(consolidated_test_names_split[0])
    m += 1
  
  eo_df = pd.DataFrame({"Submissions": generalised_submission_names,
                        "Results": eo})

  # print(eo_df)
  sns.set_theme(style="whitegrid")
  plot = sns.violinplot(data=eo_df, x="Submissions", y="Results",  split = True, inner="stick")
  plot.set_title('Equal Opportunity Performance of 10 Best Submissions: Seed '+str(seed))
  plot.set_xticklabels(plot.get_xticklabels(), rotation = 90)  
  plot.set_xlabel('Submissions')
  plot.set_ylabel('Equal Opportunity (%)')
  plt.show()

def separate_test_suite(overall_set, overall_labels):
  # print(overall_labels.size)
  #Gather all indices which are unique. (w.r.t site, sex and neurostatus)
  test_indices = determine_test_sample_indices(overall_set, overall_labels)
  train_indices = np.delete(np.arange(overall_labels.size), test_indices)

  subject_id_test = overall_set.index.values.copy() #Key_values of original dataframe
  subject_id_train = overall_set.index.values.copy() #Key_values of original dataframe

  #New Dataframe Transfer of testing data
  test_dataset = pd.DataFrame(index = subject_id_test[test_indices]) #initialise dataframe with key values with unique acquisition
  test_dataset.loc[:, overall_set.columns] = overall_set.loc[subject_id_test[test_indices]] #Copy all dataframe information w.r.t key values
  test_dataset.index.name = "subject_id"

  #New Dataframe Transfer of training data
  train_dataset = pd.DataFrame(index = subject_id_train[train_indices]) #initialise dataframe with key values with unique acquisition
  train_dataset.loc[:, overall_set.columns] = overall_set.loc[subject_id_train[train_indices]] #Copy all dataframe information w.r.t key values
  train_dataset.index.name = "subject_id"
  #Discern validity of sample. (Acquisition site has neurodiverse/neurotypical Male/Female)
  # print(test_dataset.loc[:,["participants_site", "participants_sex"]].value_counts())
  # print(train_dataset.info())
  # print(test_dataset.info())
  return train_dataset, overall_labels[train_indices], test_dataset, overall_labels[test_indices]

def determine_test_sample_indices(overall_set, overall_labels):

  test_data = []
  i = 0

  site_data = overall_set["participants_site"].values
  sex_data = overall_set["participants_sex"].values
  y = overall_labels.copy()

  #Iterate over all unique values from site, sex and 'neurostatus'
  for site_i in np.unique(site_data): #Iterate over array of unique sites [1, 2, ..., 34]
    for sex_i in np.unique(sex_data): #Iterate over aray of unique sexes ['M', 'F']
      for y_i in np.unique(y): #Iterate over array of unique labels ['0', '1']

        #Determine all indicies of data satisfy unique values being iterated over
        neuro_label = np.where(y.reshape(-1) == y_i)[0] #List of indices that equal y_i
        sex_label = np.where(sex_data.reshape(-1) == sex_i)[0] #List of indices that equal sex_i
        site_label = np.where(site_data.reshape(-1) == site_i)[0] #List of indices that equal site_i

        #Determine which indices satisfy all three above conditions
        intersection = np.intersect1d(np.intersect1d(neuro_label, sex_label), site_label)

        if intersection.shape[0] > 0: #If there is at least one scenario which satisfies all three conditions
          test_data.append(np.random.choice(intersection)) #Choose a random index
          i += 1 #Count the total unique scenarios

  test_data = np.array(sorted(test_data)) #sort the resultant array
  # print(i)
  return(test_data)

#As the function name describes, joining the original training and test dataframes together.
#Furthermore, joins the labelled outcome arrays together to maintain tracking of subject to result
#Please note both solutions preserve the original order of the two separate datasets and labels
#Finally, these have been concatenated with the resultant order: Original training dataset -> Original test dataset
def join_original_datasets(data_train, labels_train, data_test, labels_test):
  return pd.concat([data_train, data_test], ignore_index=False), np.concatenate((labels_train, labels_test))

#Function checks each index of 'dataset_one' and checks if it is 'in' 'dataset_two'.
#If there are no instances where this occurs, the function will return true (therefore having unique indices)
#If there are instances of two datasets with duplicate indices, the function will return false at the first instance.
def determine_unique_dataframe(dataset_one, dataset_two):
  dataset_one_indices = dataset_one.index.values.copy()
  dataset_two_indices = dataset_two.index.values.copy()
  for index in dataset_one_indices:
    if index in dataset_two_indices:
      return False
  return True

def sex_index_split(test_dataset):
  male_indices = []
  female_indices = []

  sex_indices = test_dataset["participants_sex"].to_numpy()
  i = 0
  while i < len(sex_indices):
    if sex_indices[i] == 'M':
      male_indices.append(i)
    else:
      female_indices.append(i)
    i += 1

  return (male_indices, female_indices)

def organise_results(name, raw_submission_results):
  # print(raw_submission_results)
  # name = "hi"
  summed_result = {}
  summed_result[name] = {}
  folds = 0
  for test_name in raw_submission_results:
    summed_result[name][test_name] = {}
    folds = 0
    for fold_number in raw_submission_results[test_name]:
      folds+=1
      for test_category_name in raw_submission_results[test_name][fold_number]:
        if test_category_name not in summed_result[name][test_name]:
          summed_result[name][test_name][test_category_name] = {}
        if "Average" in summed_result[name][test_name][test_category_name]:
          summed_result[name][test_name][test_category_name]["Average"] = raw_submission_results[test_name][fold_number][test_category_name] + summed_result[name][test_name][test_category_name]["Average"]
        else:
          summed_result[name][test_name][test_category_name]["Average"] = raw_submission_results[test_name][fold_number][test_category_name]
        summed_result[name][test_name][test_category_name][fold_number] = raw_submission_results[test_name][fold_number][test_category_name]
        # print(test_name, test_category_name, fold_number, ":", summed_result[name][test_name][test_category_name][fold_number])

  # print(summed_result[name])
  for test_name in summed_result[name]:
    for test_category_name in summed_result[name][test_name]:
      summed_result[name][test_name][test_category_name]["Average"] = summed_result[name][test_name][test_category_name]["Average"]/folds
      # print(test_name, test_category_name, summed_result[test_name][test_category_name]/folds)
  # print(folds, averaged_results)

  organised_results = pd.DataFrame.from_dict({(i, j, k): summed_result[i][j][k]
                                              for i in summed_result.keys()
                                              for j in summed_result[i].keys()
                                              for k in summed_result[i][j].keys()}, orient = 'index')
  organised_results.index.set_names(['submission', 'type', 'category'])
  # organised_results.columns = ["Average Results"]
  # print(organised_results.info())
  # print(organised_results.index)
  # print(organised_results)
  return organised_results

#Functions to run each submission
def run_pearrr_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "pearrr_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.pearrr_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.pearrr_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_abethe_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "abethe_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.abethe_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.abethe_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_amicie_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "amicie_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.amicie_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.amicie_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_ayoub_ghriss_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "ayoub_ghriss_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.ayoub_ghriss_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.ayoub_ghriss_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_lbg_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "lbg_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.lbg_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.lbg_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_mk_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "mk_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.mk_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.mk_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_nguigui_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "nguigui_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.nguigui_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.nguigui_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_Slasnista_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "Slasnista_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.Slasnista_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.Slasnista_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_vzantedeschi_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "vzantedeschi_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.vzantedeschi_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.vzantedeschi_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_wwwwmmmm_original(data_train, labels_train, data_test, labels_test, sex_test):
  name = "wwwwmmmm_original"
  print(name)
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.wwwwmmmm_original.classifier import Classifier
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  from submissions.wwwwmmmm_original.feature_extractor import FeatureExtractor

  download_data()

  warnings.filterwarnings("ignore", category=DeprecationWarning)

  fold_results = train_folds(data_train, labels_train, data_test, labels_test, Classifier, FeatureExtractor)
  fold_stat_results = process_results(fold_results, labels_test, sex_test)

  return create_dataframe(name, fold_stat_results)

def run_tests(seed):
  np.random.seed(seed)
  #Load data
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  data_train, labels_train, data_test, labels_test = load_data()

  #Display initial dataset information
  # print(data_train.info())
  # print(labels_train.size)
  # print(data_test.info())
  # print(labels_test.size)

  #Display information of initial datasets with respect to acquisition sites.
  # print(data_train["participants_site"].value_counts().sort_index())
  # print(data_test["participants_site"].value_counts().sort_index())

  #Merge both intial datasets to preserve all datasets
  merged_dataset, merged_labels = join_original_datasets(data_train, labels_train, data_test, labels_test)

  #Display information regarding merged dataset
  # print(merged_dataset.info())
  # print(merged_labels.size)
  # print(merged_dataset["participants_site"].value_counts().sort_index()) #34
  # print(merged_dataset.index)

  #Generate randomised test dataset and remove from training dataset.
  new_train_dataset, new_train_labels, new_test_dataset, new_test_labels = separate_test_suite(merged_dataset, merged_labels)
  # print(new_test_dataset.head(5))

  sex_test = sex_index_split(new_test_dataset)
  # print(sex_test)
  #Check uniqueness of training and test datasets
  # print(determine_unique_dataframe(new_train_dataset, new_test_dataset))
  # print(determine_unique_dataframe(new_train_dataset, new_train_dataset))

  #Display information of training/testing datasets and their results.
  # print(data_train.index)
  # print(new_train_dataset.index)
  # print(new_train_dataset.info())
  # print(new_train_labels.size)
  # print(new_test_dataset.info())
  # print(new_test_labels.size)

  #Display training/testing results
  # print(labels_train)
  # print(labels_test)
  # print(merged_labels)

  #Indexing a dataframe
  # print(merged_dataset.loc[10631804530197433027])

  #Display gender ratio information
  # print_gender_info()
  # gender_ratio_per_fold()
  # submissions = []
  if check_for_saved_file(seed) == False:
    #Train and test submissions

    submissions = run_pearrr_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)
    submissions = pd.concat([submissions, run_abethe_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_amicie_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_ayoub_ghriss_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_lbg_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_mk_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    # submissions = run_nguigui_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)
    submissions = pd.concat([submissions, run_nguigui_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_Slasnista_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_vzantedeschi_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    submissions = pd.concat([submissions, run_wwwwmmmm_original(new_train_dataset, new_train_labels, new_test_dataset, new_test_labels, sex_test)])
    save_predictions(seed, submissions)
  else:
    submissions = load_predictions(seed)
    submissions.set_index("submission", inplace=True)
  # for a in submissions:
  #   for b in a:
  #     # for c in b:
  #     print(b.type)
  print(submissions)
  # create_violin_graph(submissions)
  # fig= plt.figure(figsize=(90, 10))
  # submissions["Average"].plot.bar()
  # plt.xticks(rotation = 90)
  # plt.legend(loc=(1.04, 0))
  # plt.show()
  auc_roc(submissions, seed)
  general_accuracy(submissions, seed)
  equal_opportunity(submissions, seed)

def test_suite():
  x = np.random.rand()
  # x = 1
  results = {}
  ga_folds = {}
  eo_folds = {}

  ga_tests_1 = {}
  ga_tests_1['overall'] = 0.6*x
  ga_tests_1['male'] = 0.6060606060606061*x
  ga_tests_1['female'] = 0.5918367346938775*x
  ga_folds[1] = ga_tests_1

  ga_tests_2 = {}
  ga_tests_2['overall'] = 0.6347826086956522*x
  ga_tests_2['male'] = 0.6363636363636364*x
  ga_tests_2['female'] = 0.6326530612244898*x
  ga_folds[2] = ga_tests_2

  ga_tests_3 = {}
  ga_tests_3['overall'] = 0.6347826086956522*x
  ga_tests_3['male'] = 0.6363636363636364*x
  ga_tests_3['female'] = 0.6326530612244898*x
  ga_folds[3] = ga_tests_3

  ga_tests_4 = {}
  ga_tests_4['overall'] = 0.6260869565217392*x
  ga_tests_4['male'] = 0.6060606060606061*x
  ga_tests_4['female'] = 0.6530612244897959*x
  ga_folds[4] = ga_tests_4

  ga_tests_5 = {}
  ga_tests_5['overall'] = 0.6*x
  ga_tests_5['male'] = 0.6212121212121212*x
  ga_tests_5['female'] = 0.5714285714285714*x
  ga_folds[5] = ga_tests_5

  eo_tests_1 = {}
  eo_tests_1['overall'] = 0.17647058823529416*x
  eo_folds[1] = eo_tests_1

  eo_tests_2 = {}
  eo_tests_2['overall'] = 0.1642156862745099*x
  eo_folds[2] = eo_tests_2
  
  eo_tests_3 = {}
  eo_tests_3['overall'] = 0.08088235294117652*x
  eo_folds[3] = eo_tests_3
  
  eo_tests_4 = {}
  eo_tests_4['overall'] = 0.20588235294117652*x
  eo_folds[4] = eo_tests_4
  
  eo_tests_5 = {}
  eo_tests_5['overall'] = 0.15931372549019612*x
  eo_folds[5] = eo_tests_5

  results['ga'] = ga_folds
  results['eo'] = eo_folds
  return results

# group_results = {}
# results_1 = test_suite()
# results_2 = test_suite()
# # print(results_1)

# organised_1 = organise_results("test_1", results_1)
# # print(organised_1)
# organised_2 = organise_results("test_2", results_2)

# group_results = pd.concat([organised_1, organised_2])

# # group_results["first"] = organised_1
# # group_results["second"] = organised_2

# # print(group_results.info())
# # print(group_results.index)
# print(group_results)

# create_violin_graph(group_results)
# fig= plt.figure(figsize=(30, 10))
# # keys = group_results["Average"].index
# # values = group_results["Average"]
# group_results["Average"].plot.bar()
# plt.xticks(rotation = 90)
# plt.legend(loc=(1.04, 0))
# plt.show()

random_seed = 42
run_tests(random_seed)