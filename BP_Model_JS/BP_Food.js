const fs = require('fs');
const axios = require('axios');
const crypto = require('crypto');
// const { Image } = require('canvas'); // You might need to use a different library for image processing
const FormData = require('form-data');
const moment = require('moment-timezone');
const { v4: uuidv4 } = require('uuid');
const sharp = require('sharp')
const path = require('path');

// Get secret from a file
function getSecret(setting, secretsFile) {
    try {
        const secrets = JSON.parse(fs.readFileSync(secretsFile, 'utf8'));
        return secrets[setting];
    } catch (error) {
        console.error(`Error getting the secret ${setting}:`, error);
    }
}

// Resize image using Canvas or another image processing library
// async function imgSizeSharp(imgPath) {
//     try {
//         // Read the image
//         const image = sharp(imgPath);

//         // Get metadata to access image dimensions
//         const metadata = await image.metadata();

//         // Check and resize image
//         if (metadata.width > metadata.height || metadata.height > metadata.width || metadata.width === metadata.height) {
//             await image.resize(1440, 1440).toFile(imgPath); // Overwrite the original image
//             // Console log for debugging
//             // console.log("Image resized to 1440x1440");
//         }
//     } catch (error) {
//         console.error("Error resizing image:", error);
//     }
// }

async function imgSizeSharp(imgPath) {
    try {
        // Create a temporary file path
        const tempPath = path.join(path.dirname(imgPath), 'temp_' + path.basename(imgPath));
        console.log(tempPath)
        // Resize the image and save to the temporary file
        await sharp(imgPath)
            .resize(1440, 1440)
            .toFile(tempPath);

        // Replace the original file with the temporary file
        fs.renameSync(tempPath, imgPath);

        console.log("Image resized and saved.");
    } catch (error) {
        console.error("Error resizing image:", error);
    }
}

async function foodApi(imgPath, secretFile) {
    // Timestamp
    const timeStamp = moment().tz("Asia/Seoul").format("YYYYMMDDHHmmssSSS").slice(0, -1);
    console.log(timeStamp);
    // Get secrets
    const clientId = getSecret('kt_client_id', secretFile);
    const clientSecret = getSecret('kt_client_secret', secretFile);
    const signature = crypto.createHmac('sha256', clientSecret).update(`${clientId}:${timeStamp}`).digest('hex');
    console.log(signature);

    // API call setup
    const url = 'https://aiapi.genielabs.ai/kt/vision/food';
    const clientKey = getSecret('kt_client_key', secretFile);

    const headers = {
        "Accept": "*/*",
        "x-client-key": clientKey,
        "x-client-signature": signature,
        "x-auth-timestamp": timeStamp
    };
    
    const fields = {
        flag: "ALL" // or "UNSELECTED" or "CALORIE" or "NATRIUM"
    };
    
    const formData = new FormData();
    formData.append('metadata', JSON.stringify(fields));
    formData.append('media', fs.createReadStream(imgPath));
    
    return axios.post(url, formData, { headers: { ...formData.getHeaders(), ...headers } })
        .then(response => {
            if (response.status === 200) {
                console.log("Code:", response.data.code);
                // console.log("Data:", response.data.data);
                return response.data.data
            } else {
                console.log("Error:", response.status, response.statusText);
            }
        })
        .catch(error => {
            console.error("Error:", error.response.status, error.response.data);
        });
}

async function ocrApi(imgPath, secretFile) {
    // Logic similar to foodApi, adapted for OCR
    try {
        const data = fs.readFileSync(secretFile, 'utf8');
        secrets = JSON.parse(data);
    } catch (error) {
        console.error("Error reading the secrets file:", error);
    }
    
    function getSecret(setting) {
        if (secrets && secrets[setting]) {
            return secrets[setting];
        } else {
            console.error(`Set the ${setting} environment variable`);
        }
    }
    
    const apiUrl = getSecret('CLOVA_OCR_Invoke_URL');
    const secretKey = getSecret('naver_secret_key');
    
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
    formData.append('file', fs.createReadStream(imgPath));
    
    const headers = {
        'X-OCR-SECRET': secretKey,
        ...formData.getHeaders()
    };

    return axios.post(apiUrl, formData, { headers })
        .then(response => {
            // Return the data you're interested in from the .then() callback
            return response.data;
        })
        .catch(error => {
            console.error("Error in OCR API:", error);
            throw error; // Re-throw the error to be caught in processOCR
        });
}

async function odApi(imgPath) {
    let odUrl = getSecret("Object_Detection_URL",secretFile);

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

// Main execution
const basePath = '../BP/BP_Model_JS/';
const imgPath = `${basePath}test17.jpg`;
const secretFile = `${basePath}secrets.json`;

async function processOCR() {
    try {
        const ocrResult = await ocrApi(imgPath, secretFile);
        if (ocrResult.images[0].inferResult === 'ERROR') {
            console.log("ocrResult:", ocrResult.images[0].inferResult);
            imgSizeSharp(imgPath)
            const foodResult = await foodApi(imgPath, secretFile); // Assuming food_api is also an async function
            const odResult = await odApi(imgPath);
            console.log(foodResult[0])
            for (let region_num in foodResult[0]) {
                console.log(foodResult[0][region_num].prediction_top1,"\n");
                console.log(foodResult[0][region_num].prediction_top5,"\n--------------");
            }
            for (let item in odResult){
                console.log(odResult[item])
            }
        } else {
            let text = "";
            if (ocrResult.images[0].receipt.result['subResults'].length > 0) {
                ocrResult.images[0].receipt.result.subResults[0]['items'].forEach(field => {
                    text += field.name.text + "\n";
                });
            }
            console.log(text);
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

processOCR();
