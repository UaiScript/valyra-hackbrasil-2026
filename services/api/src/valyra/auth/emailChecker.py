import re
import dns.resolver

class EmailChecker():
    @staticmethod
    def formato_valido(email: str) -> bool:
        regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(regex, email) is not None
    
    @staticmethod
    def dominio_tem_mx(email: str) -> bool:
        try:
            dominio = email.split('@')[1]
            registros_mx = dns.resolver.resolve(dominio, 'MX')
            return len(registros_mx) > 0
        except Exception as e:
            return False

if __name__ == '__main__':
    pass