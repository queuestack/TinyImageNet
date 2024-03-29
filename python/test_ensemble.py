#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  5 23:25:55 2017

@author: Q
"""

import torch
from dataset import TestDataset
from vggmodel import make_vgg
from resnetmodel import make_resnet
from torch.utils.data import DataLoader
from torchvision import transforms
from torch.autograd import Variable
import pandas as pd
import sys

def test(model_name, model_number, is_ensemble):
    is_ensemble = int(is_ensemble)
    BATCH_SIZE = 100
    
    # dataset and model path
    IMG_EXT = ".JPEG"
    TEST_IMG_PATH = "../data/test/images/"
    TEST_DATA = "../data/test/test_sample_submission_kaggle.csv"
    MODEL_PATH1 = "../model/" + model_name + model_number + "_test_1.pkl"
    MODEL_PATH2 = "../model/" + model_name + model_number + "_test_2.pkl"   
   
    if is_ensemble: 
        OUTPUT_PATH = "../result/" + model_name + model_number + "_ensemble_result.csv"
    else: 
        OUTPUT_PATH = "../result/" + model_name + model_number + "_result.csv"

    is_cuda = torch.cuda.is_available()
    
    # data augmentation
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])

    # resnet 18 and 34 get 224 * 224 image as input image
    if model_name == 'resnet' and (model_number == '18' or model_number == '34'):
        transformations = transforms.Compose([
    								transforms.Scale(224),
                                    transforms.ToTensor(),
                                    normalize])
    # other models get 56 * 56 image as input    
    else:
        transformations = transforms.Compose([
                                    transforms.ToTensor(),
                                    normalize])
    
    kwargs = {'num_workers':1, 'pin_memory':True} if is_cuda else {}

    test_dataset = TestDataset(TEST_DATA, TEST_IMG_PATH, IMG_EXT, transformations)
    test_loader = DataLoader(test_dataset,
                             batch_size = BATCH_SIZE,
                             shuffle=False,
                             **kwargs)
    
    # choose model architecture
    if model_name == "vgg":
        model1 = make_vgg(model_number)
        model2 = make_vgg(model_number)        
    elif model_name == "resnet":
        model1 = make_resnet(model_number)
        model2 = make_resnet(model_number)        
    else:
        print('choose valid model among vgg and resnet')
    
    # load trained model
    if is_ensemble:        
        model1.load_state_dict(torch.load(MODEL_PATH1))
        model2.load_state_dict(torch.load(MODEL_PATH2))    
        if is_cuda:
            model1.cuda()
            model2.cuda()
        model1.eval()
        model2.eval()

    else:
        model1.load_state_dict(torch.load(MODEL_PATH1))
        if is_cuda:
            model1.cuda()    
        model1.eval()
   
    # estimate the result
    print('Testing start') 
    header = list()
    header.append('id')
    class_names = ['class_'+str(x).zfill(3) for x in range(100)]
    
    for i in range(len(class_names)):
        header.append(class_names[i])
    
    results = list()
    
    for i, (images, ids) in enumerate(test_loader):
        if is_cuda:
            images = images.cuda()
        images = Variable(images)
        outputs1 = model1(images) 
        if is_ensemble:
            outputs2 = model2(images)
        
        for j in range(len(outputs1)):
            result = list()
            result.append(ids[j])
            
            probs1 = torch.max(outputs1[j])
            # ensemble process
            if is_ensemble:
                probs2 = torch.max(outputs2[j])
	
                if probs1.max() > probs2.max():
                    output = list(outputs1[j].data)
                else:
                    output = list(outputs2[j].data)
            else:
                output = outputs1[j].data
            
            # output is log softmax
            # it is changed into softmax by exponent
            for k in range(len(output)):            
                result.append(2 ** output[k])
            results.append(result)
            
        if (i+1) % 10 == 0:      
            print ('Iter [%d/%d]'%(i+1, len(test_dataset)//BATCH_SIZE))
    
    # save result
    df = pd.DataFrame.from_records(results, columns=header)
    df.to_csv(OUTPUT_PATH, index=False)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage : python3 test_ensemble.py model_name model_number, is_ensemble')    
    else:
        test(sys.argv[1], sys.argv[2], sys.argv[3])
