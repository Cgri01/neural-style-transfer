

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';


export const sendFrameToBackend = async (imageBlob , processSize = 384) => {
    try {
        //Formdata olusturma:
        const formData = new FormData();
        formData.append('file', imageBlob, 'frame.jpg');
        formData.append("process_size" , processSize.toString());

        //Backende POST isteği gönderme:
        const response = await fetch(`${API_BASE_URL}/process_frame`, {
            method: 'POST',
            body: formData
            // Content-Type header'ını belirtmiyoruz! 
            // fetch otomatik olarak multipart/form-data boundary ekler
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.log("Backend Error:" , response.status , errorText);
            return null;
        }

        const styledImageBlob = await response.blob();

        if(!styledImageBlob.type.includes("image")) {
            console.log("Backend did not return an image file!")
            console.error("Backend did not return an image. Response type:", styledImageBlob.type);
            return null;
        }

        return styledImageBlob;
        
    } catch (error) {
        console.error("Backend connection error: " , error);
        console.error("Make sure backend works");
        return null;
        
    }
};

export const resetFilter = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/reset_filter`, {
            method: 'POST',
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            console.error("Filter resetting error:" , response.status);
            return false;
        }

        const data = await response.json();
        console.log("Filter has been resetted: " , data);
        return true;

    } catch (error) {
        console.error("Filter resetting error:" , error);
        return false;
    }
};


export const setAlpha = async (alpha) => {
    try {
        const value = Number(alpha).toFixed(2);
        const response = await fetch(`${API_BASE_URL}/set_alpha?alpha=${value}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        } );

        if (!response.ok) {
            console.error("Alpha changing error: " , response.status);
            return false;
        }

        const data = await response.json();
        console.log("Alpha has been changed: " , data);
        return true;

    } catch (error) {
        console.error("Alpha changing connection error: " , error);
        return false;
    }
};


export const healthCheck = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.ok;
    } catch (error) {
        return false;
    }
};


//KULLANILABILIR STIL LISTESI
export const getStyles = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/styles`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Style list could not receive: " , error);
        return { current_style: "starry_night" , available_styles : []};
        
    }
};


//STIL DEGISTIRME:
export const changeStyle = async (styleId) => {
    try {
        const response = await fetch(`${API_BASE_URL}/set_style?style_id=${styleId}` , {
            method : 'POST' ,
            headers : {
                'Content-Type' : 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP.${response.status}`);
        }

        const result = await response.json();
        console.log("Style changed " , result);
        return result;

    } catch (error) {
        console.error("Style change error: " , error);
        throw error;
    }
}


export const getWebSocketURL = (processSize = 384) => {
    const wsBase = API_BASE_URL.replace(/^http/i, "ws");
    return `${wsBase}/ws/video_feed?process_size=${processSize}`;
};