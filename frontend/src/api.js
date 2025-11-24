import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const conciliateFile = async (file, tol, arPrefix, apPrefix) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post(`${API_URL}/conciliate`, formData, {
            params: {
                tol: tol,
                ar_prefix: arPrefix,
                ap_prefix: apPrefix,
            },
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error uploading file:', error);
        throw error;
    }
};
