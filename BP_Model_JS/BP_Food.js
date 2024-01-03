const fs = require('fs');
const axios = require('axios');
const crypto = require('crypto');
const FormData = require('form-data');
const moment = require('moment-timezone');
const { v4: uuidv4 } = require('uuid');
const sharp = require('sharp')
const path = require('path');

// Get secret from a file
function getSecret(setting, secretsFile) {
    try {
        const secrets = JSON.parse(fs.readFileSync(secretsFile, 'utf8'));
        print(secrets)
        return secrets[setting];
    } catch (error) {
        console.error(`Error getting the secret ${setting}:`, error);
    }
}

// // Get image resizing
// async function imgResize(imgPath) {
//     try {
//         const tempPath = path.join(path.dirname(imgPath), 'temp_' + path.basename(imgPath));
//         console.log(tempPath);

//         // Read the image and get its metadata
//         const metadata = await sharp(imgPath).metadata();

//         // Define the minimum dimensions
//         const minWidth = metadata.width > metadata.height ? 1080 : 720;
//         const minHeight = metadata.width > metadata.height ? 720 : 1080;

//         // Check if the image already meets the minimum size requirements
//         if (metadata.width >= minWidth && metadata.height >= minHeight) {
//             console.log("Image already meets the minimum size requirements. No resizing needed.");
//             return;
//         }

//         // Calculate the new dimensions while maintaining aspect ratio
//         let newWidth, newHeight;
//         if (metadata.width / metadata.height > 1) {
//             // Image is wide
//             newHeight = Math.max(metadata.height, minHeight);
//             newWidth = Math.round(newHeight * (metadata.width / metadata.height));
//             if (newWidth < minWidth) {
//                 // Adjust width if it's still below minimum after resizing
//                 newWidth = minWidth;
//                 newHeight = Math.round(newWidth / (metadata.width / metadata.height));
//             }
//         } else {
//             // Image is tall
//             newWidth = Math.max(metadata.width, minWidth);
//             newHeight = Math.round(newWidth / (metadata.width / metadata.height));
//             if (newHeight < minHeight) {
//                 // Adjust height if it's still below minimum after resizing
//                 newHeight = minHeight;
//                 newWidth = Math.round(newHeight * (metadata.width / metadata.height));
//             }
//         }

//         // Resize the image and save to the temporary file
//         await sharp(imgPath)
//             .resize(newWidth, newHeight)
//             .toFile(tempPath);

//         // Replace the original file with the temporary file
//         fs.renameSync(tempPath, imgPath);

//         console.log("Image resized and saved.: ",metadata.width,metadata.height);
//     } catch (error) {
//         console.error("Error resizing image:", error);
//     }
// }



// // Function to use KT Genie Labs Food API
// async function foodApi(imgPath, secretFile) {
//     // Get Timestamp
//     const timeStamp = moment().tz("Asia/Seoul").format("YYYYMMDDHHmmssSSS").slice(0, -1);
//     // Get secrets
//     const clientId = getSecret('kt_client_id', secretFile);
//     const clientSecret = getSecret('kt_client_secret', secretFile);
//     const signature = crypto.createHmac('sha256', clientSecret).update(`${clientId}:${timeStamp}`).digest('hex');
//     const clientKey = getSecret('kt_client_key', secretFile);

//     // API call setup
//     const url = 'https://aiapi.genielabs.ai/kt/vision/food';

//     const headers = {
//         "Accept": "*/*",
//         "x-client-key": clientKey,
//         "x-client-signature": signature,
//         "x-auth-timestamp": timeStamp
//     };
    
//     const fields = {
//         flag: "ALL" // or "UNSELECTED" or "CALORIE" or "NATRIUM"
//     };
    
//     const formData = new FormData();
//     formData.append('metadata', JSON.stringify(fields));
//     formData.append('media', fs.createReadStream(imgPath));
    
//     return axios.post(url, formData, { headers: { ...formData.getHeaders(), ...headers } })
//         .then(response => {
//             if (response.status === 200) {
//                 console.log("Code:", response.data.code);
//                 // console.log("Data:", response.data.data);
//                 return response.data.data
//             } else {
//                 console.log("Error:", response.status, response.statusText);
//             }
//         })
//         .catch(error => {
//             console.error("Error:", error.response.status, error.response.data);
//         });
// }

// // Function to use Naver Clova OCR API
// async function ocrApi(imgPath, secretFile) {
//     // Logic similar to foodApi, adapted for OCR
//     try {
//         const data = fs.readFileSync(secretFile, 'utf8');
//         secrets = JSON.parse(data);
//     } catch (error) {
//         console.error("Error reading the secrets file:", error);
//     }
    
//     const apiUrl = getSecret('CLOVA_OCR_Invoke_URL',secretFile);
//     const secretKey = getSecret('naver_secret_key',secretFile);
    
//     const requestJson = {
//         'images': [
//             {
//                 'format': 'jpg',
//                 'name': 'demo'
//             }
//         ],
//         'requestId': uuidv4(),
//         'version': 'V2',
//         'timestamp': new Date().getTime()
//     };
    
//     const formData = new FormData();
//     formData.append('message', JSON.stringify(requestJson));
//     formData.append('file', fs.createReadStream(imgPath));
    
//     const headers = {
//         'X-OCR-SECRET': secretKey,
//         ...formData.getHeaders()
//     };

//     return axios.post(apiUrl, formData, { headers })
//         .then(response => {
//             // Return the data you're interested in from the .then() callback
//             return response.data;
//         })
//         .catch(error => {
//             console.error("Error in OCR API:", error);
//             throw error; // Re-throw the error to be caught in processOCR
//         });
// }

// // Function to use AI server of flask
async function odApi(imgPath,secretFile) {
    let odUrl = "http://203.241.246.109:10003/predict";

    const formData = new FormData();
    formData.append('food_image', fs.createReadStream(imgPath));

    const headers = {
        ...formData.getHeaders()
    }

    return axios.post(odUrl, formData, { headers })
        .then(response => {
            return response.data;
        })
        .catch (error => {
            console.error('Error:', error);
            throw error;
        });
}

    const basePath = '../BP/BP_Model_JS/';
    const imgPath = `${basePath}img/not_food_test6.jpg`;
    const secretFile = `${basePath}secrets.json`;

odApi(imgPath,"secrets.json")
// // Function of Main execution
// async function processApi() {

//     // request json
//     let data = {
//         // 0 : OCR , 1 : KT & OD
//         "inferResult": 0,
//         // predict Result
//         "predict": {
//             // predict food name
//             "foodNames": [],
//             // kt predict food info
//             "ktFoodsInfo": {}       
//         }
//     };

//     // Path to use files
//     const basePath = '../BP/BP_Model_JS/';
//     const imgPath = `${basePath}img/not_food_test6.jpg`;
//     const secretFile = `${basePath}secrets.json`;

//     try {
//         // OCR api call
//         const ocrResult = await ocrApi(imgPath, secretFile);
//         // If it is not a receipt image
//         if (ocrResult.images[0].inferResult === 'ERROR') {
//             /* //inferResult check point
//             console.log("ocrResult:", ocrResult.images[0].inferResult); */
//             imgResize(imgPath)
//             // KT Api & Flask server call
//             const foodResult = await foodApi(imgPath, secretFile);
//             const odResult = await odApi(imgPath,secretFile);
//             data['inferResult'] = 1
//             // console.log(foodResult[0])
//             for (let region_num in foodResult[0]) {
//                 // console.log(region_num)
//                 /*Scheduled to be converted to json format later -> kt Api ================*/
//                 // console.log(foodResult[0][region_num].prediction_top1,"\n");
//                 // console.log(foodResult[0][region_num].prediction_top5,"\n--------------");
//                 data['predict']['ktFoodsInfo'][region_num] = foodResult[0][region_num].prediction_top1
//                 data['predict']['foodNames'].push(foodResult[0][region_num].prediction_top1["food_name"])
//                 /*=========================================================================*/
//             }
//             for (let item in odResult){
//                 /*Scheduled to be converted to json format later -> Flask server===========*/
//                 // console.log(odResult[item])
//                 data['predict']['foodNames'].push(odResult[item]['Food_name'])
//                 /*=========================================================================*/
//             }
//         } else {
//             /*Scheduled to be converted to json format later -> OCR Api====================*/
//             if (ocrResult.images[0].receipt.result['subResults'].length > 0) {
//                 ocrResult.images[0].receipt.result.subResults[0]['items'].forEach(field => {
//                     data['predict']['foodNames'].push(field.name.text);
//                 });
//             }
//             /*=============================================================================*/
//         }

//         // JSON.stringify 함수를 사용하여 객체를 JSON 문자열로 변환합니다.
//         const jsonData = JSON.stringify(data, null, 4); // null과 4는 JSON을 예쁘게 출력하기 위한 옵션입니다.

//         // 파일로 저장합니다. 'data.json'은 저장될 파일의 이름입니다.
//         fs.writeFile(`${basePath}result.json`, jsonData, 'utf8', function (err) {
//             if (err) {
//                 console.log("An error occured while writing JSON Object to File.");
//                 return console.log(err);
//             }

//             console.log("JSON file has been saved.");
//         });
//     } catch (error) {
//         console.error("Error:", error);
//     }
// }

// processApi();
