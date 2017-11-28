# -*- coding: utf-8 -*-
"""
Created on Sun Oct  8 21:52:58 2017

@author: Mathu_Gopalan"""

# Read URL , 
import sys, os, csv, yaml, subprocess,time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from skimage.measure import compare_ssim
from urllib.parse import urlparse
from PIL import Image
import unittest
import util
import imutils
import cv2
import numpy as np
import pandas as pd


  
def read_config(confg):
    global BaseFolder, InputFile,SnapFolder,env_old,env_new,login_form,credentials_new
    global credentials_old,form_login,form_pass,form_submit
    global folderpath 
    global finalResult
    result_df = pd.DataFrame(columns=['path','SSIM','MSE']) 
    folderpath = {}    
    finalResult = {}
    with open(confg,'r') as ymlfile:
        cfg = yaml.load(ymlfile)
        #print (cfg)
    for section in cfg:
        BaseFolder = cfg["Path"]["BaseFolder"]
        InputFile = cfg["Path"]["InputFile"]
        SnapFolder = cfg["Path"]["SnapFolder"]
        env_old = cfg["Enviornment"]["old"]
        env_new = cfg["Enviornment"]["New"]
        login_form = cfg["Login"]["LoginPath"]
        credentials_new = cfg["Login"]["CredentialsNew"]
        credentials_old = cfg["Login"]["CredentialsOld"]
        form_login = cfg["Login"]["form_user_name"]
        form_pass = cfg["Login"]["form_user_pass"]
        form_submit = cfg["Login"]["form_user_submit"]        
    print("Config completed")
    create_basefolder(BaseFolder,SnapFolder,InputFile)

def create_basefolder(BaseFolder,SnapFolder,InputFile):
    print ("creating folders basefolder : {}, snap folder{}..".format(BaseFolder,SnapFolder))
    #directory = BaseFolder
    #snap_dir = SnapFolder
    #create base folder
    if not os.path.exists(BaseFolder):
        os.makedirs(BaseFolder)
    #create snap folder    
    if not os.path.exists(SnapFolder):
        os.makedirs(SnapFolder)
    with open(InputFile) as csvfile:
        for url in csvfile:
            parsed_url = urlparse(url)
            #print(parsed_url)
            parsed_foldername = parsed_url[2].replace('/','_')
            print("parsedfoler:{}".format(parsed_foldername))
            pathname=os.path.join(SnapFolder,parsed_foldername)
            if len(pathname)>241:
                pathname = pathname[0:240]
            elif not os.path.exists(pathname.strip()):
                os.mkdir(pathname.strip())
            folderpath.update({pathname.strip():parsed_url[2]})
    print("folder creation completed")
    
   
def login_page(flag):
    if (flag =="new"):
        i_ent = env_new
        credentials = credentials_new
    else:
        i_ent = env_old
        credentials = credentials_old
    print(i_ent,credentials)
    remdr = webdriver.Chrome()
    remdr.maximize_window()        
    remdr.get(i_ent+"/"+login_form)
    remdr.implicitly_wait(2000)
    time.sleep(2)
    remdr.find_element_by_id(form_login).send_keys(credentials.split("/")[0])
    remdr.find_element_by_id(form_pass).send_keys(credentials.split("/")[1])
    remdr.find_element_by_xpath(form_submit).click()
    remdr.implicitly_wait(200)  
    time.sleep(2)
    takeSnap(remdr,i_ent,flag)
       
  
def takeSnap(driver,env,key):
    #remdr = webdriver.Chrome()
    for k,v in folderpath.items():
        URL_snap = env + v
        driver.maximize_window()
        driver.implicitly_wait(500000)
        driver.get(URL_snap.strip())
        print("Snapping {}".format(URL_snap))
        time.sleep(3)
        driver.implicitly_wait(5000)
        util.fullpage_screenshot(driver,k,key)

def resize_image():
    # for each folder path iterate images - check dims image - resize compare 
    for k,v in folderpath.items():  
        print("Comparing Image size")
        print(k)
        old_imagepath = k+"/old_snap.png"        
        new_imagepath = k+"/new_snap.png"
        result_imagepath = k+"/result_snap.png"
        print("Old_Image:{}, \nnew_image:{}, \nresult:{}".format(old_imagepath,new_imagepath,result_imagepath))
        old_i = Image.open(old_imagepath)
        new_i = Image.open(new_imagepath)
        print("old image size:{}, new imsize:{}".format(old_i,new_i))
        if(old_i.size == new_i.size):
            print("same size")
            rx_cm = "compare -dissimilarity-threshold 1 -fuzz 10% -metric AE -highlight-color blue {0} {1} {2}".format(old_imagepath,new_imagepath,result_imagepath)
            run_win_cmd(rx_cm)
        else:
            print("diff size")
            resized_new_image = new_i.resize(old_i.size, Image.ANTIALIAS)
            resized_new_image.save(k+"/resized_new_snap.png")
            resized_i_path = k+"/resized_new_snap.png"
            rx_cm = "compare -dissimilarity-threshold 1 -fuzz 10% -metric AE -highlight-color blue {0} {1} {2}".format(old_imagepath,resized_i_path,result_imagepath)
            run_win_cmd(rx_cm)
        
def run_win_cmd(cmd):
    print("in rud cmd function")        
    result = []
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    print("process: {}".format(process))
    for line in process.stdout:
        result.append(line)
    errcode = process.returncode
    for line in result:
        print(line)
    if errcode is not None:
        raise Exception('cmd %s failed, see above for details', cmd)

def Metrics():
    global result_df
    for k,v in folderpath.items(): 
        old_i = k+"/old_snap.png"
        new_i = k+"/new_snap.png"
        new_r_i = k+"/resized_new_snap.png"
        #read opencv images
        image_a = cv2.imread(old_i)        
        if os.path.exists(new_r_i):
            image_b = cv2.imread(new_r_i)
        else:
            image_b = cv2.imread(new_i)
        print("calculating Structural Similarity Index (SSIM)..,...")
        gray_old = cv2.cvtColor(image_a, cv2.COLOR_BGR2GRAY)
        gray_new = cv2.cvtColor(image_b, cv2.COLOR_BGR2GRAY)
        # compute the Structural Similarity Index (SSIM) between the two
        # images, ensuring that the difference image is returned
        (score, diff) = compare_ssim(gray_old, gray_new, full=True)
        diff = (diff * 255).astype("uint8")
        print("SSIM: {}".format(score))
        cv2.imwrite(k+"\\diff.png", diff)
        print ("calculating MSE....")
        mse_err =mse(image_a,image_b)
        print ("MSE: {}".format(mse_err))
        file_obj = open(k+"/file.txt",'w')
        file_obj.write("SSIM :{}, MSE :{}".format(score,mse_err))
        file_obj.close()
        finalResult.update({k:"SSIM_{}_MSE_{}".format(score,mse_err)})
        result_df = result_df.append(pd.DataFrame({'path':k,'SSIM':score,'MSE':mse_err},index=[0]),ignore_index=True)
          
def mse(imageA, imageB):
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])
    return err 
def gen_HTML():
    html_file = BaseFolder+"/result.html"
    with open(html_file, 'w') as fo:
        fo.write(result_df.to_html()) 
    with open(SnapFolder+"mypage.html", 'w') as myFile:
    myFile.write('<html>')
    myFile.write('<body>')
    myFile.write('<table border="1" class="dataframe">')
    myFile.write(
    """<thead>
    <tr style="text-align: right;">
      <th></th>
      <th>MSE</th>
      <th>SSIM</th>
      <th>path</th>
    </tr>
  </thead>""")
    for index, row in result_df.iterrows():
        if(row['SSIM']>0.5 and row['SSIM']<0.7):
            color="yellow"
        elif(row['SSIM']>0.8):
            color="green"
        elif(row['SSIM']<0.5):
            color="red"
        myFile.write('<tr style="background-color:{}"><th>{}</th><td>{}</td><td>{}</td><td>D:/HCPAU/Images/_content_cf-pharma_health-hcpp...</td></tr>'.format(color,index,row['SSIM'],row['MSE']))
    myFile.write('</table>')
    myFile.write('</body>')
    myFile.write('</html>')

# the 'Mean Squared Error' between the two images is the
	# sum of the squared difference between the two images;
	# NOTE: the two images must have the same dimension	    	 	
	# return the MSE, the lower the error, the more "similar"
	# the two images are  
    
def main():
    read_config('config.yml')    
    login_page("new")
    login_page("old")
    resize_image()
    Metrics()
    gen_HTML()
    
       
        
if __name__ == "__main__":
    main()