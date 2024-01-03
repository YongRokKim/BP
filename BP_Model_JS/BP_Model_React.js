import axios from 'axios';
import moment from 'moment-timezone';
import { v4 as uuidv4 } from 'uuid';
import RNFS from 'react-native-fs'; // React Native File System
import ImageResizer from 'react-native-image-resizer';
import ImageSize from 'react-native-image-size'; 
import crypto from 'react-native-crypto';

// Get secret from a file
async function getSecret(setting) {
    try {
        const secrets = await RNFS.readFile('path_to_secrets_file', 'utf8');
        return JSON.parse(secrets)[setting];
    } catch (error) {
        console.error(`Error getting the secret ${setting}:`, error);
    }
}

// Function to use KT Genie Labs Food API
async function foodApi(imgPath, secretFile) {
    try {
        const timeStamp = moment().tz("Asia/Seoul").format("YYYYMMDDHHmmssSSS").slice(0, -1);

        const clientId = await getSecret('kt_client_id', secretFile);
        const clientSecret = await getSecret('kt_client_secret', secretFile);
        const clientKey = await getSecret('kt_client_key', secretFile);

        const signature = crypto.createHmac('sha256', clientSecret).update(`${clientId}:${timeStamp}`).digest('hex');

        const url = 'https://aiapi.genielabs.ai/kt/vision/food';

        const headers = {
            "Accept": "*/*",
            "x-client-key": clientKey,
            "x-client-signature": signature,
            "x-auth-timestamp": timeStamp
        };
        
        const fields = {
            flag: "ALL" // or "UNSELECTED" or "CALORIE" or "NATRIUM"
        };
        
        let formData = new FormData();
        formData.append('metadata', JSON.stringify(fields));
        formData.append('media', {
            uri: imgPath,
            type: 'image/jpeg', // Adjust type based on your image
            name: 'image.jpg', // image file name
        });

        const response = await axios.post(url, formData, { headers: { ...headers }, });
        if (response.status === 200) {
            console.log("Code:", response.data.code);
            return response.data.data;
        } else {
            console.log("Error:", response.status, response.statusText);
        }
    } catch (error) {
        console.error("Error:", error.response ? error.response.status : error);
    }
}

async function ocrApi(imgPath, secretFile) {
    try {
        const apiUrl = await getSecret('CLOVA_OCR_Invoke_URL', secretFile);
        const secretKey = await getSecret('naver_secret_key', secretFile);
        
        const requestJson = {
            'images': [
                {
                    'format': 'jpg',
                    'name': 'demo'
                }
            ],
            'requestId': uuidv4(),
            'version': 'V2',
            'timestamp': new Date().getTime()
        };
        
        const formData = new FormData();
        formData.append('message', JSON.stringify(requestJson));
        formData.append('file', {
            uri: imgPath, // File URI
            type: 'image/jpeg', // Assuming the image is a jpeg
            name: 'image.jpg', // Name of the file
        });

        const headers = {
            'X-OCR-SECRET': secretKey,
            ...formData.getHeaders()
        };

        const response = await axios.post(apiUrl, formData, { headers });
        return response.data;
    } catch (error) {
        console.error("Error in OCR API:", error);
        throw error;
    }
}

// Function to use AI server of flask
async function odApi(imgPath, secretFile) {
    try {
        const odUrl = await getSecret("Object_Detection_URL", secretFile);

        const formData = new FormData();
        formData.append('food_image', {
            uri: imgPath, // File URI
            type: 'image/jpeg', // Assuming the image is a jpeg
            name: 'image.jpg', // Name of the file
        });

        const headers = {
            ...formData.getHeaders()
        };

        const response = await axios.post(odUrl, formData, { headers });
        return response.data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}


// Function of Main execution
async function processApi() {

    // request json
    let data = {
        // 0 : OCR , 1 : KT & OD
        "inferResult": 0,
        // predict Result
        "predict": {
            // predict food name
            "foodNames": [],
            // kt predict food info
            "ktFoodsInfo": {}       
        }
    };

    // Path to use files
    const basePath = '../BP/BP_Model_JS/';
    const imgPath = `${basePath}img/not_food_test6.jpg`;
    const secretFile = `${basePath}secrets.json`;

    try {
        // OCR api call
        const ocrResult = await ocrApi(imgPath, secretFile);
        // If it is not a receipt image
        if (ocrResult.images[0].inferResult === 'ERROR') {
            /* //inferResult check point
            console.log("ocrResult:", ocrResult.images[0].inferResult); */
            imgResize(imgPath)
            // KT Api & Flask server call
            const foodResult = await foodApi(imgPath, secretFile);
            const odResult = await odApi(imgPath,secretFile);
            data['inferResult'] = 1
            // console.log(foodResult[0])
            for (let region_num in foodResult[0]) {
                // console.log(region_num)
                /*Scheduled to be converted to json format later -> kt Api ================*/
                // console.log(foodResult[0][region_num].prediction_top1,"\n");
                // console.log(foodResult[0][region_num].prediction_top5,"\n--------------");
                data['predict']['ktFoodsInfo'][region_num] = foodResult[0][region_num].prediction_top1
                data['predict']['foodNames'].push(foodResult[0][region_num].prediction_top1["food_name"])
                /*=========================================================================*/
            }
            for (let item in odResult){
                /*Scheduled to be converted to json format later -> Flask server===========*/
                // console.log(odResult[item])
                data['predict']['foodNames'].push(odResult[item]['Food_name'])
                /*=========================================================================*/
            }
        } else {
            /*Scheduled to be converted to json format later -> OCR Api====================*/
            if (ocrResult.images[0].receipt.result['subResults'].length > 0) {
                ocrResult.images[0].receipt.result.subResults[0]['items'].forEach(field => {
                    data['predict']['foodNames'].push(field.name.text);
                });
            }
            /*=============================================================================*/
        }

        // JSON.stringify 함수를 사용하여 객체를 JSON 문자열로 변환합니다.
        const jsonData = JSON.stringify(data, null, 4); // null과 4는 JSON을 예쁘게 출력하기 위한 옵션입니다.

        // 파일로 저장합니다. 'data.json'은 저장될 파일의 이름입니다.
        RNFS.writeFile(`${basePath}result.json`, jsonData, 'utf8', function (err) {
            if (err) {
                console.log("An error occured while writing JSON Object to File.");
                return console.log(err);
            }

            console.log("JSON file has been saved.");
        });
    } catch (error) {
        console.error("Error:", error);
    }
}

processApi();
