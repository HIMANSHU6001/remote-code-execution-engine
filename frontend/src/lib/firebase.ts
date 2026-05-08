import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, GithubAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCmRN1OC1Z9pd8Qda9uZSVNP5oB3r2JFxE",
  authDomain: "runspace-5c913.firebaseapp.com",
  projectId: "runspace-5c913",
  storageBucket: "runspace-5c913.firebasestorage.app",
  messagingSenderId: "493101280454",
  appId: "1:493101280454:web:5c640c0a4a3771112bfbc7",
  measurementId: "G-TB5JZMECBL"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const githubProvider = new GithubAuthProvider();
